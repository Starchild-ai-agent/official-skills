import sys, json, uuid, asyncio
sys.path.append('/app')
from services.message_service import get_message_service

async def main():
    if len(sys.argv) < 5:
        return
    user_id = sys.argv[1]
    thread_id = sys.argv[2]
    role = sys.argv[3]
    content = sys.argv[4]
    
    svc = get_message_service()
    payload = [{
        'message_id': str(uuid.uuid4()),
        'role': role,
        'content': content,
        'message_type': 'text'
    }]
    await svc.insert_messages_batch(user_id, thread_id, payload)

if __name__ == '__main__':
    asyncio.run(main())
