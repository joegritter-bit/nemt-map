from email_handler import get_latest_mfa_code

print("🕵️‍♂️ Robot is checking Gmail for MTM codes...")

try:
    # This tries to find a code sent in the last 5 minutes
    code = get_latest_mfa_code()
    
    if code:
        print(f"✅ SUCCESS! Found code: {code}")
    else:
        print("⚠️ Connection worked, but no RECENT code found.")
        print("   (This is normal if you haven't requested one in the last 5 mins)")
        
except Exception as e:
    print(f"❌ ERROR: Could not connect to Gmail.\n{e}")