import asyncio
from quiz_solver import submit_answer

async def main():
    res = await submit_answer(
        "https://httpbin.org/post",  # replace with webhook URL to inspect
        email="24f3002790@ds.study.iitm.ac.in",
        secret="24f3002790_shreyas",
        quiz_url="https://example.com/test",
        answer=123
    )
    print(res)

asyncio.run(main())
