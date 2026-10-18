import logging
from typing import Optional, Dict, Any
from app.services.gcp import db

logger = logging.getLogger("motivation-app")


class UserService:
    @staticmethod
    def get_user_ref(username: str):
        if not db:
            return None
        return db.collection("users").document(username.strip().lower())

    @staticmethod
    def get_user_data(username: str) -> Dict[str, Any]:
        user_ref = UserService.get_user_ref(username)
        if not user_ref:
            return {}
        try:
            doc = user_ref.get()
            return doc.to_dict() if doc.exists else {}
        except Exception as e:
            logger.error(f"Error fetching user data for {username}: {e}")
            return {}

    @staticmethod
    def upsert_user(username: str, goal: Optional[str] = None, voice: str = "female") -> bool:
        user_ref = UserService.get_user_ref(username)
        if not user_ref:
            return False
        try:
            updates = {"name": username.strip(), "preferred_voice": voice}
            if goal:
                updates["goal"] = goal.strip()
            user_ref.set(updates, merge=True)
            return True
        except Exception as e:
            logger.error(f"Error updating user profile for {username}: {e}")
            return False

    @staticmethod
    def record_feedback(username: str, action: str, quote: str) -> Dict[str, Any]:
        user_ref = UserService.get_user_ref(username)
        if not user_ref:
            return {"status": "error", "message": "Database unavailable"}

        try:
            user_doc = user_ref.get()
            user_data = user_doc.to_dict() if user_doc.exists else {}

            if action == "like" and quote:
                liked = user_data.get("liked_quotes", [])
                if quote not in liked:
                    liked.append(quote)
                user_ref.set({"liked_quotes": liked}, merge=True)
                return {"status": "liked", "total_likes": len(liked)}

            elif action == "dislike" and quote:
                disliked = user_data.get("disliked_quotes", [])
                if quote not in disliked:
                    disliked.append(quote)
                user_ref.set({"disliked_quotes": disliked}, merge=True)
                return {"status": "disliked", "total_dislikes": len(disliked)}

            return {"status": "ignored"}
        except Exception as e:
            logger.error(f"Error recording feedback for {username}: {e}")
            return {"status": "error", "message": str(e)}
