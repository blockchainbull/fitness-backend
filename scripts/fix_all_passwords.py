#!/usr/bin/env python3
"""
Definitive Password Fix Script
This script will ensure ALL users can login on both web and Flutter
"""

import asyncio
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from database import SessionLocal, User
import traceback

# Use the SAME password context as your API
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Known passwords for your development users
KNOWN_PASSWORDS = {
    "guest@example.com": "defaultpassword123",
    "test-user@example.com": "defaultpassword123", 
    "broski@123.com": "broski@123.com",
    "brother@123.com": "brother@123.com", 
    "bhai@123.com": "bhai@123.com",
    "bhai1@123.com": "bhai1@123.com",
    "bhai2@123.com": "bhai2@123.com", 
    "bhai3@123.com": "bhai3@123.com",
    "hs@123.com": "hs@123.com",
    "mastorat@123.com": "mastorat@123.com",
    "masti@123.com": "masti@123.com",
}

async def fix_all_passwords():
    """Fix all user passwords to use the unified system"""
    print("🔧 Definitive Password Fix Script")
    print("=" * 50)
    
    async with SessionLocal() as session:
        try:
            # Get all users
            result = await session.execute(select(User))
            users = result.scalars().all()
            
            print(f"👥 Found {len(users)} users to fix")
            
            for user in users:
                print(f"\n🔧 Fixing user: {user.name} ({user.email})")
                
                # Get the known password for this user
                known_password = KNOWN_PASSWORDS.get(user.email)
                
                if known_password:
                    print(f"   🔑 Using known password")
                    # Generate new hash with passlib (same as API)
                    new_hash = pwd_context.hash(known_password)
                    
                    # Update both fields
                    user.password = new_hash
                    user.password_hash = new_hash
                    user.updated_at = datetime.utcnow()
                    
                    print(f"   ✅ Password standardized with passlib")
                else:
                    # Set a default password for unknown users
                    default_password = "TempPassword123!"
                    new_hash = pwd_context.hash(default_password)
                    
                    user.password = new_hash
                    user.password_hash = new_hash
                    user.updated_at = datetime.utcnow()
                    
                    print(f"   🔄 Set temporary password: {default_password}")
            
            # Commit all changes
            await session.commit()
            print(f"\n✅ All {len(users)} users fixed!")
            
            # Print login instructions
            print("\n" + "=" * 50)
            print("📋 LOGIN INSTRUCTIONS:")
            print("=" * 50)
            for email, password in KNOWN_PASSWORDS.items():
                print(f"Email: {email}")
                print(f"Password: {password}")
                print()
            
            print("For other users:")
            print("Password: TempPassword123!")
            print("=" * 50)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            traceback.print_exc()
            await session.rollback()

if __name__ == "__main__":
    asyncio.run(fix_all_passwords())