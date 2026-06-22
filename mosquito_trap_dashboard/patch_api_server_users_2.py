import re

file_path = '/home/dung/.openclaw/workspace-VP2_codex/projects/mosquito_trap_dashboard/api_server_v11.py'
with open(file_path, 'r') as f:
    content = f.read()

# The routes added previously might have been placed after the `if __name__ == '__main__': app.run(...)` block.
# We need to move them before that block.

if "if __name__ == '__main__':" in content:
    parts = content.split("if __name__ == '__main__':")
    main_block = "if __name__ == '__main__':" + parts[1]
    
    # Check if the user endpoints are in the main_block
    if "@app.route('/users')" in main_block:
        # It's at the end, so we need to move it up.
        # Find where it starts
        user_mgmt_start = main_block.find("# ===========================================================================")
        if user_mgmt_start != -1:
            user_endpoints = main_block[user_mgmt_start:]
            # Remove from main_block
            main_block = main_block[:user_mgmt_start]
            
            # Put back before main_block
            new_content = parts[0] + user_endpoints + "\n" + main_block
            with open(file_path, 'w') as f:
                f.write(new_content)
            print("Fixed: Moved user endpoints before app.run()")
        else:
            print("Could not find user endpoints start marker.")
    else:
        print("User endpoints are not after app.run(). Check routing.")
else:
    print("Could not find app.run() block.")
