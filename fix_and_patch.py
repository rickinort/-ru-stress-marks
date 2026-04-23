import os

path_accent = r'C:\Users\rickinort\AppData\Local\Programs\Python\Python312\Lib\site-packages\ruaccent\accent_model.py'
path_omograph = r'C:\Users\rickinort\AppData\Local\Programs\Python\Python312\Lib\site-packages\ruaccent\omograph_model.py'

def cleanup_and_patch(fpath):
    if not os.path.exists(fpath):
        return
    
    with open(fpath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 1. Cleanup old patches
    clean_lines = []
    skip = False
    for line in lines:
        if '# Patch:' in line:
            skip = True
            continue
        if skip:
            if 'self.session.run(None, inputs)' in line:
                skip = False
                clean_lines.append(line)
                continue
            if 'input_names = ' in line or 'if \'token_type_ids\'' in line or 'import numpy' in line or 'inputs[\'token_type_ids\']' in line:
                continue
            else:
                skip = False # End of patch block
        clean_lines.append(line)
        
    # 2. Apply fresh patch
    final_lines = []
    patched = False
    for line in clean_lines:
        if 'self.session.run(None, inputs)' in line:
            indent = line[:line.find('self.session.run')]
            final_lines.append(f"{indent}# Patch: ensure mandatory token_type_ids\n")
            final_lines.append(f"{indent}input_names = [i.name for i in self.session.get_inputs()]\n")
            final_lines.append(f"{indent}if 'token_type_ids' in input_names and 'token_type_ids' not in inputs:\n")
            final_lines.append(f"{indent}    import numpy as np\n")
            final_lines.append(f"{indent}    inputs['token_type_ids'] = np.zeros_like(inputs['input_ids'])\n")
            final_lines.append(line)
            patched = True
        else:
            final_lines.append(line)
            
    with open(fpath, 'w', encoding='utf-8') as f:
        f.writelines(final_lines)
    print(f"Handled {fpath}")

cleanup_and_patch(path_accent)
cleanup_and_patch(path_omograph)
