import os
from typing import Dict, List, Optional
from datetime import datetime

import firebase_admin
from firebase_admin import credentials, firestore


class FirebaseService:
    """
    Firebase (Firestore) service for replacing MongoDB.

    Uses:
    - Collection `users`              for user profiles
    - Collection `chatMessages`       for chat history
    - Collection `userActivityLogs`   for activity logging
    - Collection `jobApplications`    for job applications
    - Collection `employerContacts`   for employer/contact data
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirebaseService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._initialized = True
            self.db = None
            self._init_firebase()

    def _init_firebase(self) -> None:
        """
        Initialize Firebase Admin with service account and Firestore client.

        Required env var:
        - FIREBASE_SERVICE_ACCOUNT_PATH: absolute/relative path to service-account JSON
        """
        try:
            service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "service-account.json")
            if not os.path.exists(service_account_path):
                print(f"FIREBASE_SERVICE_ACCOUNT_PATH not set and {service_account_path} not found; Firebase disabled.")
                return

            if not firebase_admin._apps:
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred)

            self.db = firestore.client()
            print("Firebase Firestore initialized.")
        except Exception as e:
            print(f"Error initializing Firebase: {e}")
            self.db = None

    def is_available(self) -> bool:
        """Check if Firebase Firestore is ready."""
        return self.db is not None

    # ---------- Chat messages ----------
    async def save_chat_message(
        self,
        user_id: str,
        role: str,
        content: str,
        page_context: Optional[str] = None,
    ) -> Optional[str]:
        if not self.db:
            return None

        try:
            doc = {
                "userId": user_id,
                "role": role,
                "content": content,
                "pageContext": page_context,
                "createdAt": datetime.utcnow(),
            }
            ref = self.db.collection("chatMessages").add(doc)
            return ref[1].id
        except Exception as e:
            print(f"Error saving chat message to Firebase: {e}")
            return None

    async def get_chat_history(self, user_id: str, limit: int = 50) -> List[Dict]:
        if not self.db:
            return []

        try:
            query = (
                self.db.collection("chatMessages")
                .where("userId", "==", user_id)
                .order_by("createdAt", direction=firestore.Query.DESCENDING)
                .limit(limit)
            )
            docs = query.stream()
            history: List[Dict] = []
            for d in docs:
                data = d.to_dict()
                data["id"] = d.id
                history.append(data)
            # reverse to oldest → newest
            return list(reversed(history))
        except Exception as e:
            print(f"Error getting chat history from Firebase: {e}")
            return []

    # ---------- User profile ----------
    async def save_user_profile(self, user_id: str, profile_data: Dict) -> Optional[str]:
        if not self.db:
            return None

        try:
            profile_data["updatedAt"] = datetime.utcnow()
            self.db.collection("users").document(user_id).set(profile_data, merge=True)
            return user_id
        except Exception as e:
            print(f"Error saving user profile to Firebase: {e}")
            return None

    async def get_user_profile(self, user_id: str) -> Optional[Dict]:
        if not self.db:
            return None

        try:
            doc = self.db.collection("users").document(user_id).get()
            if not doc.exists:
                return None
            data = doc.to_dict()
            data["id"] = doc.id
            return data
        except Exception as e:
            print(f"Error getting user profile from Firebase: {e}")
            return None

    # ---------- Activity logs ----------
    async def log_user_activity(
        self, user_id: str, activity_type: str, metadata: Optional[Dict] = None
    ) -> Optional[str]:
        if not self.db:
            return None

        try:
            doc = {
                "userId": user_id,
                "activityType": activity_type,
                "metadata": metadata or {},
                "createdAt": datetime.utcnow(),
            }
            ref = self.db.collection("userActivityLogs").add(doc)
            return ref[1].id
        except Exception as e:
            print(f"Error logging user activity to Firebase: {e}")
            return None

    # ---------- Job applications ----------
    async def save_job_application(self, application_data: Dict) -> Optional[str]:
        if not self.db:
            return None

        try:
            application_data.setdefault("createdAt", datetime.utcnow())
            ref = self.db.collection("jobApplications").add(application_data)
            return ref[1].id
        except Exception as e:
            print(f"Error saving application to Firebase: {e}")
            return None

    # ---------- Employer contacts ----------
    async def get_employer_contact(self, company_id: str) -> Optional[Dict]:
        """
        Get employer contact information from Firestore.
        Collection: employerContacts
        Document ID: company_id
        """
        if not self.db:
            return None

        try:
            doc = self.db.collection("employerContacts").document(company_id).get()
            if not doc.exists:
                return None
            data = doc.to_dict()
            data["companyId"] = doc.id
            return data
        except Exception as e:
            print(f"Error getting employer contact from Firebase: {e}")
            return None


# Create singleton instance
firebase_service = FirebaseService()