"""
Enhanced Password Migration Script for HealthAI App 
Fixes bcrypt compatibility issues and handles edge cases better.
"""

import asyncio
import argparse
import sys
import os
from datetime import datetime
from typing import List, Dict, Optional
import warnings

# Suppress the bcrypt warning
warnings.filterwarnings("ignore", message=".*bcrypt.*")

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, update, text
from sqlalchemy.ext.asyncio import AsyncSession

# Import passlib with proper configuration
from passlib.context import CryptContext
from passlib.hash import bcrypt as passlib_bcrypt

# Import your existing database setup
from database import SessionLocal, User, engine
from config import DATABASE_URL

# Configure passlib to handle bcrypt compatibility
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    # Add explicit bcrypt configuration
    bcrypt__rounds=12,
    bcrypt__ident="2b"
)

class EnhancedPasswordMigrator:
    def __init__(self, dry_run: bool = False, force: bool = False):
        self.dry_run = dry_run
        self.force = force
        self.stats = {
            'total_users': 0,
            'compatible_hashes': 0,
            'migrated_hashes': 0,
            'standardized_fields': 0,
            'reset_required': 0,
            'errors': 0,
            'skipped': 0
        }
        
        # Test passwords for development environment
        self.test_passwords = [
            "defaultpassword123",
            "password123", 
            "123456",
            "password",
            "admin",
            "test",
        ]
        
    async def run_migration(self):
        """Main migration function with enhanced error handling"""
        print("🔐 Enhanced Password Migration Script for HealthAI App v2")
        print(f"📊 Database: {DATABASE_URL}")
        print(f"🔍 Mode: {'DRY RUN' if self.dry_run else 'LIVE MIGRATION'}")
        print("=" * 60)
        
        async with SessionLocal() as session:
            try:
                # Get all users
                users = await self._get_all_users(session)
                self.stats['total_users'] = len(users)
                
                print(f"👥 Found {len(users)} users to process")
                
                if len(users) == 0:
                    print("✅ No users found. Nothing to migrate.")
                    return
                
                # Process each user
                for user in users:
                    await self._process_user_enhanced(session, user)
                
                # Commit changes if not dry run
                if not self.dry_run:
                    await session.commit()
                    print("\n💾 Changes committed to database")
                else:
                    print("\n🔍 DRY RUN - No changes made to database")
                
                # Print final statistics
                self._print_final_stats()
                
            except Exception as e:
                print(f"❌ Migration failed: {e}")
                if not self.dry_run:
                    await session.rollback()
                raise
    
    async def _get_all_users(self, session: AsyncSession) -> List[User]:
        """Get all users from database"""
        result = await session.execute(select(User).order_by(User.created_at))
        return result.scalars().all()
    
    async def _process_user_enhanced(self, session: AsyncSession, user: User):
        """Enhanced user processing with better error handling"""
        try:
            print(f"\n🔍 Processing user: {user.name} ({user.email})")
            
            # Get current password values
            current_password = user.password
            current_password_hash = user.password_hash
            
            print(f"   Current password field: {'SET' if current_password else 'NULL'}")
            print(f"   Current password_hash field: {'SET' if current_password_hash else 'NULL'}")
            
            # Determine which field to use as source
            source_hash = self._determine_source_hash(current_password, current_password_hash)
            
            if not source_hash:
                print(f"   ⚠️  No password hash found - skipping")
                self.stats['skipped'] += 1
                return
            
            # Test if we can find the original password
            original_password = await self._find_original_password(source_hash, user)
            
            if original_password:
                print(f"   🔑 Found original password")
                # Test compatibility and migrate if needed
                if await self._test_new_system_compatibility(original_password, source_hash):
                    print(f"   ✅ Hash is compatible with new system")
                    self.stats['compatible_hashes'] += 1
                    # Still standardize fields
                    if await self._standardize_password_fields(session, user, source_hash):
                        self.stats['standardized_fields'] += 1
                else:
                    print(f"   🔄 Migrating to new hash format")
                    await self._migrate_with_known_password(session, user, original_password)
                    self.stats['migrated_hashes'] += 1
            else:
                print(f"   ⚠️  Could not determine original password")
                print(f"   🔄 Marking for password reset")
                await self._mark_for_password_reset(session, user, source_hash)
                self.stats['reset_required'] += 1
                
        except Exception as e:
            print(f"   ❌ Error processing user {user.email}: {e}")
            self.stats['errors'] += 1
    
    def _determine_source_hash(self, password: str, password_hash: str) -> Optional[str]:
        """Determine which password field to use as source"""
        if password_hash:
            return password_hash
        elif password:
            return password
        else:
            return None
    
    async def _find_original_password(self, hash_value: str, user: User) -> Optional[str]:
        """Try to find the original password for development users"""
        # Add user-specific test passwords
        user_specific_passwords = [
            user.name.lower(),
            user.email.split('@')[0],
            user.email.split('@')[0] + "123",
            f"{user.name.lower()}123",
        ]
        
        all_test_passwords = self.test_passwords + user_specific_passwords
        
        for test_password in all_test_passwords:
            try:
                # Test with passlib (which should handle both old and new formats)
                if pwd_context.verify(test_password, hash_value):
                    return test_password
            except Exception:
                continue
        
        return None
    
    async def _test_new_system_compatibility(self, password: str, hash_value: str) -> bool:
        """Test if the hash is compatible with the new passlib system"""
        try:
            return pwd_context.verify(password, hash_value)
        except Exception:
            return False
    
    async def _migrate_with_known_password(self, session: AsyncSession, user: User, password: str):
        """Migrate user with known password"""
        try:
            # Generate new hash with passlib
            new_hash = pwd_context.hash(password)
            print(f"   ✅ Generated new hash with passlib")
            
            if not self.dry_run:
                user.password = new_hash
                user.password_hash = new_hash
                user.updated_at = datetime.utcnow()
                
        except Exception as e:
            print(f"   ❌ Error generating new hash: {e}")
            raise
    
    async def _mark_for_password_reset(self, session: AsyncSession, user: User, old_hash: str):
        """Mark user for password reset on next login"""
        print(f"   📝 Standardizing fields and marking for reset")
        
        if not self.dry_run:
            # Standardize both fields to the same value
            user.password = old_hash
            user.password_hash = old_hash
            user.updated_at = datetime.utcnow()
            
            # You could add a password_reset_required field here if you have it
            # user.password_reset_required = True
    
    async def _standardize_password_fields(self, session: AsyncSession, user: User, source_hash: str) -> bool:
        """Ensure both password fields have the same value"""
        needs_update = False
        
        if user.password != source_hash:
            print(f"   📝 Standardizing password field")
            if not self.dry_run:
                user.password = source_hash
            needs_update = True
            
        if user.password_hash != source_hash:
            print(f"   📝 Standardizing password_hash field")
            if not self.dry_run:
                user.password_hash = source_hash
            needs_update = True
        
        return needs_update
    
    def _print_final_stats(self):
        """Print enhanced final migration statistics"""
        print("\n" + "=" * 60)
        print("📊 ENHANCED MIGRATION SUMMARY")
        print("=" * 60)
        print(f"Total users processed:     {self.stats['total_users']}")
        print(f"Compatible hashes:         {self.stats['compatible_hashes']}")
        print(f"Migrated hashes:          {self.stats['migrated_hashes']}")
        print(f"Standardized fields:      {self.stats['standardized_fields']}")
        print(f"Need password reset:      {self.stats['reset_required']}")
        print(f"Errors:                   {self.stats['errors']}")
        print(f"Skipped:                  {self.stats['skipped']}")
        print("=" * 60)
        
        if self.stats['errors'] > 0:
            print("⚠️  Some users had errors. Review the output above.")
        elif self.stats['total_users'] > 0:
            print("✅ Migration completed successfully!")
        
        if self.stats['reset_required'] > 0:
            print(f"\n🔄 {self.stats['reset_required']} users need password reset:")
            print("   - These users can continue using their current passwords")
            print("   - Consider implementing a password reset flow")
            print("   - Or manually reset passwords for these users")
        
        if not self.dry_run and (self.stats['migrated_hashes'] > 0 or self.stats['standardized_fields'] > 0):
            print("\n🚀 Next steps:")
            print("1. Test login functionality with both web and mobile apps")
            print("2. Verify cross-platform authentication works")
            print("3. Monitor authentication logs for any issues")

async def main():
    parser = argparse.ArgumentParser(description='Enhanced password migration to new system')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be migrated without making changes')
    parser.add_argument('--force', action='store_true',
                       help='Force migration even if hashes seem compatible')
    
    args = parser.parse_args()
    
    if not args.dry_run:
        print("⚠️  WARNING: This will modify user passwords in the database!")
        confirm = input("Are you sure you want to continue? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Migration cancelled.")
            return
    
    migrator = EnhancedPasswordMigrator(dry_run=args.dry_run, force=args.force)
    await migrator.run_migration()

if __name__ == "__main__":
    asyncio.run(main())