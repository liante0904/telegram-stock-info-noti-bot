import os
import re
import sys

def refactor_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.splitlines()
    new_lines = []
    
    # Check if loguru is already there
    if 'from loguru import logger' in content:
        has_loguru = True
    else:
        has_loguru = False

    in_except_block = False
    except_indent = 0
    
    import_inserted = False
    
    # We'll try to insert loguru after the last import line or after the docstring
    last_import_idx = -1
    for i, line in enumerate(lines):
        if line.lstrip().startswith(('import ', 'from ')):
            last_import_idx = i

    for i, line in enumerate(lines):
        stripped = line.lstrip()
        indent_size = len(line) - len(stripped)
        
        # Insert loguru import
        if not has_loguru and not import_inserted:
            # Insert after the last import line, or at i=0 if no imports
            if last_import_idx != -1:
                if i == last_import_idx + 1:
                    new_lines.append('from loguru import logger')
                    import_inserted = True
            else:
                # No imports found, insert before the first non-comment non-empty line
                if stripped and not stripped.startswith('#'):
                    new_lines.append('from loguru import logger')
                    import_inserted = True

        # Remove logging imports and getLogger
        if stripped.startswith('import logging'):
            continue
        if 'logging.getLogger(' in line:
            # If it's an assignment like self.logger = logging.getLogger(__name__)
            if '=' in line:
                continue
            # If it's just logging.getLogger(__name__).info(...)
            line = line.replace('logging.getLogger(__name__).', 'logger.')
            line = line.replace('logging.getLogger(__name__)', 'logger')
            # Check again
            if 'logging.getLogger' in line:
                 continue

        # Handle except blocks
        if stripped.startswith('except '):
            in_except_block = True
            except_indent = indent_size
        elif in_except_block:
            if stripped: # non-empty line
                if indent_size <= except_indent:
                    in_except_block = False
            # if empty line, we stay in except block state until we see next indent

        # Replace print
        if stripped.startswith('print(') or stripped.startswith('print '):
            # Try to match print(...)
            # Using a simpler approach: replace 'print(' with 'logger.info(' 
            # but we need to choose between info, error, debug.
            
            # Extract content to check for complex objects
            content_match = re.search(r'print\s*\((.*)\)', stripped)
            if content_match:
                print_content = content_match.group(1)
            else:
                print_content = stripped[5:].strip()

            is_complex = False
            if re.search(r'(_list|_data|json_|records|rows|total_data)', print_content):
                is_complex = True

            prefix = line[:indent_size]
            
            if in_except_block:
                log_func = 'logger.error'
            elif is_complex:
                log_func = 'logger.debug'
            else:
                log_func = 'logger.info'

            # Reconstruction
            if stripped.startswith('print('):
                new_line = line.replace('print(', f'{log_func}(', 1)
            else:
                # print "message" -> logger.info("message")
                new_line = f"{prefix}{log_func}({print_content})"
            
            new_lines.append(new_line)
            continue

        # Replace existing logger calls if any
        # Handle self.logger
        line = line.replace('self.logger.error(', 'logger.error(')
        line = line.replace('self.logger.info(', 'logger.info(')
        line = line.replace('self.logger.warning(', 'logger.warning(')
        line = line.replace('self.logger.debug(', 'logger.debug(')
        line = line.replace('self.logger.exception(', 'logger.exception(')
        
        new_lines.append(line)

    # Final check for loguru import if it wasn't inserted
    if not has_loguru and not import_inserted:
        new_lines.insert(0, 'from loguru import logger')

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines) + '\n')

    print(f"Refactored: {file_path}")

if __name__ == "__main__":
    files = [
        'scraper.py',
        'scrap_af_main.py',
        'models/DataManager.py',
        'models/FirmInfo.py',
        'models/GeminiManager.py',
        'models/OracleManager.py',
        'models/PostgreSQLManager.py',
        'models/SQLiteManager.py',
        'models/WebScraper.py',
    ]
    
    modules_dir = 'modules'
    for f in os.listdir(modules_dir):
        if f.endswith('.py') and f != '__init__.py':
            files.append(os.path.join(modules_dir, f))

    for file_path in files:
        if os.path.exists(file_path):
            try:
                refactor_file(file_path)
            except Exception as e:
                print(f"Error refactoring {file_path}: {e}")
        else:
            print(f"File not found: {file_path}")
