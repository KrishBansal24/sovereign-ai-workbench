from tui.app import SovereignTUI
import asyncio

async def run():
    app = SovereignTUI()
    async with app.run_test() as p:
        await p.pause()
        print(list(app.query('#document-picker')))

if __name__ == "__main__":
    asyncio.run(run())
