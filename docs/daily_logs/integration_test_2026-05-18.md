# Integration Test Report - 2026-05-18

## Smoke Test Results
| Tool | Input | Output Type | Pass/Fail | Time (ms) |
|------|-------|-------------|-----------|-----------|
| read_file | `{'path': 'workspace/test_dummy.txt', 'start_line': 0, 'num_lines': 0}` | str | PASS | 1 |
| browser_read_page_text | `{'browser': ''}` | str | PASS | 2661 |
| web_search | `{'query': 'test', 'num_results': '5'}` | str | PASS | 8761 |
| alert | `{'message': 'test'}` | str | PASS | 2955 |
| ocr_image | `{'path': 'workspace/test_dummy.txt', 'engine': None}` | str | PASS | 0 |
| plugin_health_check | `{}` | dict | PASS | 10 |
| calculate | `{'expression': 'test'}` | str | PASS | 0 |
| code_complexity | `{'file_path': 'test'}` | str | PASS | 0 |
| competitive_intel | `{'competitors': None}` | str | PASS | 84675 |
| diff_summarizer | `{'old_text': 'test', 'new_text': 'test'}` | str | PASS | 0 |
| calculate_tax | `{'amount': 1.0}` | float | PASS | 0 |
| greet_user | `{'name': 'test'}` | str | PASS | 0 |
| create_plugin | `{'name': 'test', 'code': 'test', 'description': ''}` | str | PASS | 0 |
| research_loop | `{'topic': 'test', 'rounds': '3'}` | str | PASS | 27713 |
| url_safety_check | `{'url': 'https://example.com'}` | str | PASS | 777 |
| click_element_by_name | `{'label': 'test'}` | str | PASS | 444 |

## Tool Chain Results
- web_search -> fetch_url -> write_file: **PASS**
- read_file -> word_count -> write_file: **PASS**
- terminal_command -> capture_output -> grep_file: **PASS**

## Error Recovery Results
- Missing/Invalid argument handling: **PASS**

## Integration Health
**GOOD**