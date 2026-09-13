import sys
sys.path.insert(0, '.')
import traceback
from app.api.routes.knowledge import ask_knowledge, AskRequest

try:
    print(ask_knowledge(AskRequest(question='and pump. Cite the source document and page numbers for every major recommendation.')))
except Exception as e:
    traceback.print_exc()
