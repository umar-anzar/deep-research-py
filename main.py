import asyncio
from dotenv import load_dotenv

from src.feedback import generate_feedback
from src.deep_research import deep_research, write_final_answer, write_final_report

load_dotenv()

async def main():

    query = input("Enter your research query: ").strip()

    default_breadth = 4
    default_depth = 2

    while True:
        try:
            breadth_input = input(f"Specify research breadth (recommended: 3-10, default: {default_breadth}): ").strip()
            depth_input = input(f"Specify research depth (recommended: 1-5, default: {default_depth}): ").strip()

            breadth = int(breadth_input) if breadth_input else default_breadth
            depth = int(depth_input) if depth_input else default_depth

            if 1 <= breadth <= 10 and 1 <= depth <= 5:
                break
            else:
                print("Please enter values within the valid ranges: breadth (3-10), depth (1-5).")
        except ValueError:
            print("Invalid input. Please enter integers for both breadth and depth.")

    is_report_input = input("Generate report? (yes/no or y/n): ").strip().lower()
    is_report = is_report_input in ("yes", "y")
    
    num_questions = 3
    questions = await generate_feedback(query, num_questions)

    follow_up_answers = []
    for question in questions:
        answer = input(f"{question}: ").strip()
        follow_up_answers.append(f"Q: {question}\nA: {answer}")

    combined_query = f"Initial Query: {query}\nFollow-up Questions and Answers:\n" + "\n".join(follow_up_answers)

    search_result = await deep_research(combined_query, breadth=breadth, depth=depth)

    if is_report:
        output = await write_final_report(combined_query, search_result.learnings, search_result.visited_urls)
    else:
        output = await write_final_answer(combined_query, search_result.learnings)
    
    print("\nFinal Output:\n")
    print(output)

if __name__ == "__main__":
    asyncio.run(main())
