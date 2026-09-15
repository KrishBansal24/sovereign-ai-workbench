import pytest
import json
import asyncio
from textual.widgets import TextArea, Select
from tui.app import SovereignTUI

from tui.services.api_client import APIClient

class MockClient(APIClient):
    async def health(self): return {"backend": "online", "ollama": "available"}
    async def documents(self): return [{"document_id": "doc1", "filename": "test.csv", "file_type": "csv", "index_eligible": False, "structured_metadata": {"columns": ["asset", "vibration_mm_s_rms"]}}]
    async def artifacts(self): return []
    async def jobs(self): return []
    async def indexed_documents(self): return []
    async def close(self): pass
    async def chat(self, *args, **kwargs): return {}
    async def analysis(self, *args, **kwargs): return {}
    
    def __init__(self):
        self.chat_calls = 0
        self.analysis_calls = 0
        self.chat_responses = []
        self.analysis_responses = []
        self.analysis_args = []
        
    async def chat(self, message: str, **kwargs):
        self.chat_calls += 1
        if self.chat_responses:
            return self.chat_responses.pop(0)
        return {"response": "{}"}
        
    async def analysis(self, payload):
        self.analysis_calls += 1
        self.analysis_args.append(payload)
        if self.analysis_responses:
            return self.analysis_responses.pop(0)
        return {"result": {}, "row_count": 0}

def test_data_nl_valid_mapping():
    mock_client = MockClient()
    app = SovereignTUI()
    app.client = mock_client
    app.documents = {"doc1": {"structured_metadata": {"columns": ["asset", "vibration_mm_s_rms"]}}}
    
    async def exercise():
        async with app.run_test(size=(120, 60)) as pilot:
            await pilot.pause()
            await pilot.click("#nav-data")
            app.query_one("#dataset-picker", Select).set_options([("Doc", "doc1")])
            app.query_one("#dataset-picker", Select).value = "doc1"
            
            # Test A: Valid mapping
            mock_client.chat_responses = [{"response": json.dumps({
                "operation": "group_average",
                "category_column": "asset",
                "numeric_column": "vibration_mm_s_rms"
            })}]
            mock_client.analysis_responses = [{"result": {"averages": {"P-204": 3.85}}, "row_count": 100}]
            
            app.query_one("#data-question", TextArea).text = "Which asset has the highest average vibration?"
            await pilot.click("#data-ask-ai")
            await pilot.pause()
            
            print(str(app.query_one("#data-result").render()))
            assert mock_client.analysis_calls == 1
            args = mock_client.analysis_args[0]
            assert args["operation"] == "group_average"
            assert args["group_by"] == "asset"
            assert args["value_column"] == "vibration_mm_s_rms"
    asyncio.run(exercise())

def test_data_nl_nonexistent_column():
    mock_client = MockClient()
    app = SovereignTUI()
    app.client = mock_client
    app.documents = {"doc1": {"structured_metadata": {"columns": ["asset"]}}}
    
    async def exercise():
        async with app.run_test(size=(120, 60)) as pilot:
            await pilot.pause()
            await pilot.click("#nav-data")
            app.query_one("#dataset-picker", Select).set_options([("Doc", "doc1")])
            app.query_one("#dataset-picker", Select).value = "doc1"
            
            # Test B: Nonexistent column
            mock_client.chat_responses = [{"response": json.dumps({
                "operation": "summary",
                "numeric_column": "nonexistent_col"
            })}]
            
            app.query_one("#data-question", TextArea).text = "Summary of nonexistent_col?"
            await pilot.click("#data-ask-ai")
            await pilot.pause()
            
            assert mock_client.analysis_calls == 0
    asyncio.run(exercise())

def test_data_nl_unsupported_operation():
    mock_client = MockClient()
    app = SovereignTUI()
    app.client = mock_client
    app.documents = {"doc1": {"structured_metadata": {"columns": ["asset"]}}}
    
    async def exercise():
        async with app.run_test(size=(120, 60)) as pilot:
            await pilot.pause()
            await pilot.click("#nav-data")
            app.query_one("#dataset-picker", Select).set_options([("Doc", "doc1")])
            app.query_one("#dataset-picker", Select).value = "doc1"
            
            # Test C: Unsupported operation
            mock_client.chat_responses = [{"response": json.dumps({
                "operation": "arbitrary_python"
            })}]
            
            app.query_one("#data-question", TextArea).text = "Do something unsupported"
            await pilot.click("#data-ask-ai")
            await pilot.pause()
            
            assert mock_client.analysis_calls == 0
    asyncio.run(exercise())

def test_data_nl_ambiguous_request():
    mock_client = MockClient()
    app = SovereignTUI()
    app.client = mock_client
    app.documents = {"doc1": {"structured_metadata": {"columns": ["asset"]}}}
    
    async def exercise():
        async with app.run_test(size=(120, 60)) as pilot:
            await pilot.pause()
            await pilot.click("#nav-data")
            app.query_one("#dataset-picker", Select).set_options([("Doc", "doc1")])
            app.query_one("#dataset-picker", Select).value = "doc1"
            
            # Test D: Ambiguous request
            mock_client.chat_responses = [{"response": json.dumps({
                "explanation_needed": "I need a little more detail."
            })}]
            
            app.query_one("#data-question", TextArea).text = "Tell me something interesting."
            await pilot.click("#data-ask-ai")
            await pilot.pause()
            
            assert mock_client.analysis_calls == 0
    asyncio.run(exercise())

def test_data_nl_deterministic_display():
    mock_client = MockClient()
    app = SovereignTUI()
    app.client = mock_client
    app.documents = {"doc1": {"structured_metadata": {"columns": ["asset"]}}}
    
    async def exercise():
        async with app.run_test(size=(120, 60)) as pilot:
            await pilot.pause()
            await pilot.click("#nav-data")
            app.query_one("#dataset-picker", Select).set_options([("Doc", "doc1")])
            app.query_one("#dataset-picker", Select).value = "doc1"
            
            # Tests E and F
            mock_client.chat_responses = [
                {"response": json.dumps({"operation": "summary"})},
                {"response": "The highest was 999.99"} # Malicious explanation changes 3.85 to 999.99
            ]
            mock_client.analysis_responses = [{"result": {"P-204": 3.85}, "row_count": 100}]
            
            app.query_one("#data-question", TextArea).text = "Summary"
            await pilot.click("#data-ask-ai")
            await pilot.pause()
            
            # The UI should display the deterministic value 3.85, not just the model's 999.99
            result_text = str(app.query_one("#data-result").render())
            assert "3.85" in result_text
            assert "999.99" in result_text
    asyncio.run(exercise())
