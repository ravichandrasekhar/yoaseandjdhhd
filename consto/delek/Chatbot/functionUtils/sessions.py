
conversation_history = {}

class GetSession:
    def __init__(self):
        pass
    def get_session_id(sessionid):
        session_id = str(sessionid)
        if session_id not in conversation_history:
            conversation_history[session_id] = []
        return session_id

    def get_conversation_history(session_id):
        return conversation_history.get(session_id, [])

    def save_conversation_history(session_id, history):
        conversation_history[session_id] = history
        return conversation_history
    
    # def get_prev_questions(session_id):
    #     return conversation_history.get("prev_questions", [])
    
    # def save_prev_questions(session_id, prev_questions):
    #     # if session_id not in conversation_history:
    #     #     conversation_history[session_id] = {"history":[],"prev_questions":[]}
    #     for i in prev_questions:
    #         conversation_history[session_id]["prev_questions"] = i
    #         return conversation_history