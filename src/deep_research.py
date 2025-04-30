import json
import os
import math
import asyncio
import logging
from typing import Optional
from pydantic import BaseModel, Field
from firecrawl.firecrawl import SearchResponse
from firecrawl import FirecrawlApp, ScrapeOptions


from .prompt import system_prompt
from .providers import generate_text, get_model, trim_prompt, generate_object



LOG = logging.getLogger("my_logger")

LOG.setLevel(logging.DEBUG) 
console_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
LOG.addHandler(console_handler)



# Helper function to compact lists (removes falsy values like None, False, '', etc.)
def compact(lst):
    return [item for item in lst if item]

# Class to limit concurrency
class PLimit:
    def __init__(self, concurrency):
        self.semaphore = asyncio.Semaphore(concurrency)

    async def run(self, coro_func, *args, **kwargs):
        async with self.semaphore:
            return await coro_func(*args, **kwargs)



class ResearchProgress(BaseModel):
    current_depth: int
    total_depth: int
    current_breadth: int
    total_breadth: int
    current_query: Optional[str] = None
    total_queries: int
    completed_queries: int

class ResearchResult(BaseModel):
    learnings: list[str]
    visited_urls: list[str]


class SERPQuery(BaseModel):
    query: str = Field(description="The SERP query")
    research_goal: str = Field(
        description="First talk about the goal of the research that this query is meant to accomplish, then go deeper into how to advance the research once the results are found, mention additional research directions. Be as specific as possible, especially for additional research directions."
    )

class FinalReportResponse(BaseModel):
    report_markdown: str = Field(description="Final report on the topic in Markdown")

class FinalAnswerResponse(BaseModel):
    exact_answer: str = Field(description="The final answer, make it short and concise, just the answer, no other text")


# Constants
CONCURRENCY_LIMIT = int(os.getenv("FIRECRAWL_CONCURRENCY", 2))

# Initialize Firecrawl with optional API key and optional base URL
firecrawl_client = FirecrawlApp(
    api_key=os.getenv("FIRECRAWL_KEY"),
    api_url=os.getenv("FIRECRAWL_BASE_URL"),
)


# Function to generate SERP queries
async def generate_serp_queries(query: str, numQueries: int = 3, learnings: Optional[list[str]] = None):
    learnings_str = f"Here are some learnings from previous research, use them to generate more specific queries: {', '.join(learnings)}" if learnings else ''
    prompt = f"Given the following prompt from the user, generate a list of SERP queries to research the topic. Return a maximum of {numQueries} queries, but feel free to return less if the original prompt is clear. Make sure each query is unique and not similar to each other: <prompt>{query}</prompt>\n\n{learnings_str}"
    
    class SERPQueries(BaseModel):
        queries: list[SERPQuery] = Field(description=f"List of SERP queries, max of {numQueries}")

    res = await generate_object(
        model=get_model(),
        system=system_prompt(),
        prompt=prompt,
        schema=SERPQueries
    )
    
    LOG.info(f"Created {len(res.queries)} queries {res.model_dump_json(indent=2)}")
    return res.queries[:numQueries]

# Function to process the SERP result
async def process_serp_result(
        query: str, 
        result: SearchResponse, 
        numLearnings: int = 3, 
        numFollowUpQuestions: int = 3
    ):
    
    contents = compact([item.get('markdown') for item in result.data])
    contents = [trim_prompt(content, 25_000) for content in contents]
    
    LOG.info(f"Ran {query}, found {len(contents)} contents")

    class SERPSearch(BaseModel):
        learnings: list[str] = Field(description=f"List of learnings, max of {numLearnings}")
        follow_up_questions: list[str] = Field(
            description=f"List of follow-up questions to research the topic further, max of {numFollowUpQuestions}"
        )
        
    prompt = trim_prompt(
        f"Given the following contents from a SERP search for the query <query>{query}</query>, generate a list of learnings from the contents. " 
        f"Return a maximum of {numLearnings} learnings, but feel free to return less if the contents are clear. " 
        f"Make sure each learning is unique and not similar to each other. "
        f"The learnings should be concise and to the point, as detailed and information dense as possible. "
        f"Make sure to include any entities like people, places, companies, products, things, etc in the learnings, as well as any exact metrics, numbers, or dates. "
        f"The learnings will be used to research the topic further.\n\n<contents>{contents}</contents>")
    
    res = await generate_object(
        model=get_model(),
        abort_timeout=60_000,
        schema=SERPSearch,
        system=system_prompt(),
        prompt=prompt
    )
    
    LOG.info(f"Created {len(res.learnings)} learnings {json.dumps(res.learnings, indent=2)}")
    return res


async def deep_research(
    query: str,
    breadth: int,
    depth: int,
    learnings: list[str] = [],
    visited_urls: list[str] = [],
) -> ResearchResult:

    serp_queries = await generate_serp_queries(query, breadth, learnings)
    
    limit = PLimit(CONCURRENCY_LIMIT)

    async def process_query(serp_query: SERPQuery) -> ResearchResult:
        try:
            result = await asyncio.to_thread(lambda: firecrawl_client.search(
                serp_query.query,
                timeout=15000,
                limit=5,
                scrape_options=ScrapeOptions(formats=["markdown"])
            ))
            
            newUrls = compact([ item["url"] for item in result.data if item.get("url") ])

            new_breadth = math.ceil(breadth / 2)
            new_depth = depth - 1

            new_learnings = await process_serp_result(
                query=serp_query.query,
                result=result,
                numFollowUpQuestions=new_breadth,
            )

            all_learnings = learnings + new_learnings.learnings
            all_urls = visited_urls + newUrls

            if new_depth > 0:
                LOG.info(f"Researching deeper, breadth: {new_breadth}, depth: {new_depth}")

                next_query = f"""
                Previous research goal: {serp_query.research_goal}
                Follow-up research directions: {''.join(f'\n{q}' for q in new_learnings.follow_up_questions)}
                """.strip()

                return await deep_research(
                    query=next_query,
                    breadth=new_breadth,
                    depth=new_depth,
                    learnings=all_learnings,
                    visited_urls=all_urls
                )
            
            
            return ResearchResult(learnings=all_learnings, visited_urls=all_urls)
            
        except Exception as e:
            if "Timeout" in str(e):
                LOG.error(f"Timeout error running query: {serp_query.query}: {e}")
            else:                
                LOG.error(f"Error running query: {serp_query.query}: {e}")
            return ResearchResult(learnings=[], visited_urls=[])

    results: list[ResearchResult] = await asyncio.gather(*[limit.run(process_query, serp_query) for serp_query in serp_queries])

    return ResearchResult(
        learnings=[item for sublist in results for item in sublist.learnings],  # Collect and deduplicate results
        visited_urls=[item for sublist in results for item in sublist.visited_urls]  # Same here for URLs
    )


async def write_final_report(prompt: str, learnings: list[str], visited_urls: list[str]) -> str:
    learnings_string = "\n".join(f"<learning>\n{learning}\n</learning>" for learning in learnings)

    full_prompt = trim_prompt(f"""
        Given the following prompt from the user, write a final report on the topic using the learnings from research. 
        Make it as detailed as possible, aim for 3 or more pages, include ALL the learnings from research:

        <prompt>{prompt}</prompt>

        Here are all the learnings from previous research:

        <learnings>
        {learnings_string}
        </learnings>
    """)
    
    report_markdown = await generate_text(
        model=get_model(),
        system=system_prompt(),
        prompt=full_prompt
    )

    urls_section = "\n\n## Sources\n\n" + "\n".join(f"- {url}" for url in visited_urls)
    return report_markdown + urls_section


async def write_final_answer(prompt: str, learnings: list[str]) -> str:
    learnings_string = "\n".join(f"<learning>\n{learning}\n</learning>" for learning in learnings)

    full_prompt = trim_prompt(f"""
        Given the following prompt from the user, write a final answer on the topic using the learnings from research. 
        Follow the format specified in the prompt. Do not yap or babble or include any other text than the answer besides the format specified in the prompt. 
        Keep the answer as concise as possible - usually it should be just a few words or maximum a sentence. 
        Try to follow the format specified in the prompt (for example, if the prompt is using Latex, the answer should be in Latex. 
        If the prompt gives multiple answer choices, the answer should be one of the choices).

        <prompt>{prompt}</prompt>

        Here are all the learnings from research on the topic that you can use to help answer the prompt:

        <learnings>
        {learnings_string}
        </learnings>
    """)
    
    res = await generate_object(
        model=get_model(),
        system=system_prompt(),
        prompt=full_prompt,
        schema=FinalAnswerResponse
    )

    return res.exact_answer
