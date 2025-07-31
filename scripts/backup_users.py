"""
Backup user data before migration
"""

import asyncio
import json
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from database import SessionLocal, User

async def backup_users():
    """Create a backup of all user data"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"user_backup_{timestamp}.json"
    
    async with SessionLocal() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        
        user_data = []
        for user in users:
            user_dict = {
                'id': str(user.id),
                'name': user.name,
                'email': user.email,
                'password': user.password,
                'password_hash': user.password_hash,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'updated_at': user.updated_at.isoformat() if user.updated_at else None,
            }
            user_data.append(user_dict)
        
        with open(backup_file, 'w') as f:
            json.dump(user_data, f, indent=2, default=str)
        
        print(f"✅ Backed up {len(users)} users to {backup_file}")

if __name__ == "__main__":
    asyncio.run(backup_users())