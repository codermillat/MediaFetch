import os
from supabase import create_client, Client
from dotenv import load_dotenv
from typing import Dict, Any
from postgrest.base_request_builder import APIResponse

load_dotenv()

class SupabaseClient:
    def __init__(self):
        url: str = os.environ.get("SUPABASE_URL", "")
        key: str = os.environ.get("SUPABASE_ANON_KEY", "")
        if not url or not key:
            raise ValueError("Supabase URL and key must be set in .env file")
        self.client: Client = create_client(url, key)

    def get_binding_code(self, code: str) -> APIResponse:
        return self.client.table('binding_codes').select("*").eq('code', code).execute()

    def get_user_binding(self, telegram_user_id: int, instagram_username: str) -> APIResponse:
        return self.client.table('user_bindings').select("*").eq('telegram_user_id', telegram_user_id).eq('instagram_username', instagram_username).execute()

    def get_binding_by_code(self, code: str) -> APIResponse:
        return self.client.table('binding_codes').select("*").eq('code', code).execute()

    def get_user_by_telegram_id(self, telegram_user_id: int) -> APIResponse:
        return self.client.table('users').select("*").eq('telegram_user_id', telegram_user_id).execute()

    def create_user_binding(self, data: Dict[str, Any]) -> APIResponse:
        return self.client.table('user_bindings').insert(data).execute()

    def create_binding_code(self, data: Dict[str, Any]) -> APIResponse:
        return self.client.table('binding_codes').insert(data).execute()

    def update_binding_status(self, binding_id: int, status: str, data: Dict[str, Any]) -> APIResponse:
        return self.client.table('user_bindings').update(data).eq('id', binding_id).eq('binding_status', status).execute()

    def mark_binding_code_used(self, code: str, binding_id: int) -> APIResponse:
        return self.client.table('binding_codes').update({'is_used': True}).eq('code', code).eq('id', binding_id).execute()

    def update_user_binding_status(self, user_id: int, status: str) -> APIResponse:
        return self.client.table('users').update({'binding_status': status}).eq('id', user_id).execute()

    def get_user_bindings(self, telegram_user_id: int) -> APIResponse:
        return self.client.table('user_bindings').select("*").eq('telegram_user_id', telegram_user_id).execute()

    def get_bindings_by_instagram_username(self, instagram_username: str) -> APIResponse:
        return self.client.table('user_bindings').select("*").eq('instagram_username', instagram_username).execute()

    def create_content_delivery(self, data: Dict[str, Any]) -> APIResponse:
        return self.client.table('content_deliveries').insert(data).execute()

    def update_content_delivery(self, delivery_id: str, data: Dict[str, Any]) -> APIResponse:
        return self.client.table('content_deliveries').update(data).eq('id', delivery_id).execute()
