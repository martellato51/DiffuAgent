# Matcher 검토 리포트: smoke_explicit_state_tree
각 turn마다 gold hop과 generated unit의 hybrid 매칭 결과를 정리한 문서다. primary match가 없을 때도 P0 deterministic best candidate를 같이 보여주어 matcher threshold, judge 보정, scoring 품질을 검토할 수 있게 했다.
범례: 정확=exact, 의미=LLM judge semantic, 부분=partial, 미매칭=wrong/no primary. `valid/schema`는 각각 provided tool name 여부와 schema validation 통과 여부를 의미한다.
기준 산출물: `v2_hybrid_matches.jsonl`; best candidate는 `v2_match_candidates.jsonl`의 1순위 후보다.

## 전체 요약
- turns=70, units=149, state_view_modes=['tree']
- match_strength_counts: exact=26, partial=30, semantic=3, wrong=90
- match_method_counts: hybrid_judge_confirm=5, hybrid_judge_downgrade=10, hybrid_judge_override=19, hybrid_judge_rescue=12, hybrid_p0=103

## multi_turn_base_35 turn 0
- 목표: Find a file named 'config.py' somewhere deep in the file system and once you have located it, display the last line of the first occuring file.
- State view: `tree`
- Gold hop: h1: `cd(folder='projects')`; h2: `cd(folder='deep_folder')`; h3: `tail(file_name='config.py',lines=1)`
- 매칭 개수: 부분=1, 미매칭=3; 미매칭 gold=['h1', 'h2']
- 검토 플래그: 제공되지 않은 tool 사용: u1:find_file; 제공되지 않은 tool 사용: u2:read_file; 제공되지 않은 tool 사용: u3:find_file; 제공되지 않은 tool 사용: u4:read_file; LLM judge override/rescue/downgrade 포함; 미매칭 gold hop: h1,h2

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. find_file(name="config.py")` | False/False | 미매칭 | - | h3: `tail({"file_name": "config.py", "lines": 1})` (10) | missing_tool_schema; argument_overlap:config.py;schema_invalid; no_candidate_above_threshold |
| `2. read_file(file_name=$1, lines=1)` | False/False | 미매칭 | - | h3: `tail({"file_name": "config.py", "lines": 1})` (40) | missing_tool_schema; parameter_overlap:file_name,lines;argument_overlap:file_name,lines;schema_invalid;unresolved_input; no_candidate_above_threshold |
| `3. find_file(name="real_config.py")` | False/False | 미매칭 | - | h1: `cd({"folder": "projects"})` (0) | missing_tool_schema; schema_invalid; no_candidate_above_threshold |
| `4. read_file(file_name=$3, lines=1)` | False/False | 부분 | h3: `tail({"file_name": "config.py", "lines": 1})` (40) | h3: `tail({"file_name": "config.py", "lines": 1})` (40) | missing_tool_schema; parameter_overlap:file_name,lines;argument_overlap:file_name,lines;schema_invalid;unresolved_input; hybrid_judge_rescue; judge=partial@0.74; judge_reason=Th... |

## multi_turn_base_35 turn 1
- 목표: This is actually not what I want. Could you display the entire content of the second file found.
- State view: `tree`
- Gold hop: h4: `cat(file_name='real_config.py')`
- 매칭 개수: 정확=1, 미매칭=2; 미매칭 gold=[]

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. cd(folder='projects')` | True/True | 미매칭 | - | h4: `cat({"file_name": "real_config.py"})` (25) | schema_valid; argument_overlap:cat,real_config.py;schema_valid; no_candidate_above_threshold |
| `2. cd(folder='deep_folder')` | True/True | 미매칭 | - | h4: `cat({"file_name": "real_config.py"})` (5) | schema_valid; no_candidate_above_threshold |
| `3. cat(file_name='real_config.py')` | True/True | 정확 | h4: `cat({"file_name": "real_config.py"})` (135) | h4: `cat({"file_name": "real_config.py"})` (135) | schema_valid; exact_tool_name;parameter_overlap:file_name;argument_overlap:file_name,real_config.py;schema_valid |

## multi_turn_base_35 turn 2
- 목표: Store the differences of the two file in a new file call diff.txt.
- State view: `tree`
- Gold hop: h5: `diff(file_name1='config.py',file_name2='real_config.py')`; h6: `touch(file_name='diff.txt')`; h7: `echo(content='- Initialization of the system+ Real Config.',file_name='diff.txt')`
- 매칭 개수: 부분=1, 미매칭=1; 미매칭 gold=['h6', 'h7']
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u1; 높은 점수 후보이나 primary 미매칭: u2->h5(85); LLM judge override/rescue/downgrade 포함; 미매칭 gold hop: h6,h7

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. diff(file1='config.py', file2='real_config.py', output_name='diff.txt')` | True/False | 부분 | h5: `diff({"file_name1": "config.py", "file_name2": "real_config.py"})` (130) | h5: `diff({"file_name1": "config.py", "file_name2": "real_config.py"})` (130) | missing_required: file_name1, file_name2; unknown_parameters: file1, file2, output_name; exact_tool_name;argument_overlap:config.py,diff,real_config.py;schema_invalid; hybrid_ju... |
| `2. cat(file_name='diff.txt')` | True/True | 미매칭 | - | h5: `diff({"file_name1": "config.py", "file_name2": "real_config.py"})` (85) | schema_valid; function_mention;schema_valid; no_candidate_above_threshold |

## multi_turn_base_39 turn 0
- 목표: I need you to set up a fresh folder named 'WebDevProjects' wherever you're currently working.
- State view: `tree`
- Gold hop: h1: `mkdir(dir_name='WebDevProjects')`
- 매칭 개수: (없음); 미매칭 gold=['h1']
- 검토 플래그: 미매칭 gold hop: h1; 생성된 parsed unit 없음

Parsed generated unit이 없다.

## multi_turn_base_39 turn 1
- 목표: Populate the 'WebDevProjects' folder with 3 files:, 'styles.css', 'index.html', and 'script.js' with content 'Hello World!','Hi World!', 'Halo World!' in each.
- State view: `tree`
- Gold hop: h2: `cd(folder='WebDevProjects')`; h3: `touch(file_name='styles.css')`; h4: `echo(content='Hello World!', file_name='styles.css')`; h5: `touch(file_name='index.html')`; h6: `echo(content='Hi World!', file_name='index.html')`; h7: `touch(file_name='script.js')`; h8: `echo(content='Halo World!', file_name='script.js')`
- 매칭 개수: 정확=3; 미매칭 gold=['h2', 'h3', 'h5', 'h7']
- 검토 플래그: 미매칭 gold hop: h2,h3,h5,h7

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. echo(file_name='WebDevProjects/styles.css', content='Hello World!')` | True/True | 정확 | h4: `echo({"content": "Hello World!", "file_name": "styles.css"})` (175) | h4: `echo({"content": "Hello World!", "file_name": "styles.css"})` (175) | schema_valid; exact_tool_name;parameter_overlap:content,file_name;argument_overlap:content,file_name,hello,hello world!,styles.css,world;schema_valid |
| `2. echo(file_name='WebDevProjects/index.html', content='Hi World!')` | True/True | 정확 | h6: `echo({"content": "Hi World!", "file_name": "index.html"})` (175) | h6: `echo({"content": "Hi World!", "file_name": "index.html"})` (175) | schema_valid; exact_tool_name;parameter_overlap:content,file_name;argument_overlap:content,file_name,hi,hi world!,world;schema_valid |
| `3. echo(file_name='WebDevProjects/script.js', content='Halo World!')` | True/True | 정확 | h8: `echo({"content": "Halo World!", "file_name": "script.js"})` (175) | h8: `echo({"content": "Halo World!", "file_name": "script.js"})` (175) | schema_valid; exact_tool_name;parameter_overlap:content,file_name;argument_overlap:content,file_name,halo,halo world!,world;schema_valid |

## multi_turn_base_39 turn 2
- 목표: What's the second file name by system order? Don't list out hidden files.
- State view: `tree`
- Gold hop: h9: `ls()`
- 매칭 개수: 부분=1, 미매칭=3; 미매칭 gold=[]
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u2; schema 오류 또는 arg/param wrapper 문제: u3; schema 오류 또는 arg/param wrapper 문제: u4; 높은 점수 후보이나 primary 미매칭: u2->h9(100); 높은 점수 후보이나 primary 미매칭: u3->h9(100); LLM judge override/rescue/downgrade 포함

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. cd(folder='WebDevProjects')` | True/True | 미매칭 | - | h9: `ls({})` (5) | schema_valid; no_candidate_above_threshold |
| `2. ls(file_name='styles.css')` | True/False | 미매칭 | - | h9: `ls({})` (100) | unknown_parameters: file_name; exact_tool_name;schema_invalid; no_candidate_above_threshold |
| `3. ls(file_name='script.js')` | True/False | 미매칭 | - | h9: `ls({})` (100) | unknown_parameters: file_name; exact_tool_name;schema_invalid; no_candidate_above_threshold |
| `4. ls(file_name='index.html')` | True/False | 부분 | h9: `ls({})` (100) | h9: `ls({})` (100) | unknown_parameters: file_name; exact_tool_name;schema_invalid; hybrid_judge_confirm; judge=partial@0.86; judge_reason=The generated action is related by tool name but does not p... |

## multi_turn_base_39 turn 3
- 목표: Can you display the content of the first file by system order?
- State view: `tree`
- Gold hop: h10: `cat(file_name='styles.css')`
- 매칭 개수: 정확=1, 미매칭=1; 미매칭 gold=[]

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. cd(folder='WebDevProjects')` | True/True | 미매칭 | - | h10: `cat({"file_name": "styles.css"})` (35) | schema_valid; argument_overlap:cat,file_name,styles.css;schema_valid; no_candidate_above_threshold |
| `2. cat(file_name='styles.css')` | True/True | 정확 | h10: `cat({"file_name": "styles.css"})` (135) | h10: `cat({"file_name": "styles.css"})` (135) | schema_valid; exact_tool_name;parameter_overlap:file_name;argument_overlap:file_name,styles.css;schema_valid |

## multi_turn_base_50 turn 0
- 목표: Hey there, I noticed that all of my car doors seem to have locked themselves up, and with my schedule being pretty tight today, I'm in quite a pinch. I could really use your help to get those doors unlocked. It'd be fantastic if you could also switch on the headlights. It's ge...
- State view: `tree`
- Gold hop: h1: `lockDoors(unlock=True, door=['driver', 'passenger', 'rear_left', 'rear_right'])`; h2: `setHeadlights(mode='on')`
- 매칭 개수: 부분=1, 미매칭=1; 미매칭 gold=['h1']
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u1; schema 오류 또는 arg/param wrapper 문제: u2; 높은 점수 후보이나 primary 미매칭: u1->h1(150); LLM judge override/rescue/downgrade 포함; 미매칭 gold hop: h1

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. lockDoors(param={"unlock": True, "door": ["driver", "passenger", "rear_left", "front_right"]})` | True/False | 미매칭 | - | h1: `lockDoors({"unlock": true, "door": ["driver", "passenger", "rear_left", "rear_right"]})` (150) | missing_required: door, unlock; unknown_parameters: param; exact_tool_name;argument_overlap:door,driver,lockdoors,passenger,rear_left,unlock;schema_invalid; hybrid_judge_downgra... |
| `2. setHeadlights(param={"mode": "on"})` | True/False | 부분 | h2: `setHeadlights({"mode": "on"})` (110) | h2: `setHeadlights({"mode": "on"})` (110) | missing_required: mode; unknown_parameters: param; exact_tool_name;argument_overlap:mode;schema_invalid; hybrid_judge_override; judge=partial@0.95; judge_reason=The action match... |

## multi_turn_base_55 turn 0
- 목표: If the fuel level is lower than 10, then go ahead and add double that amount. Let's assume I will also head out right after, so feel free to start the engine using the necessary mode.
- State view: `tree`
- Gold hop: h1: `displayCarStatus('fuel')`; h2: `fillFuelTank(15.0)`; h3: `lockDoors(unlock=False, door=['driver', 'passenger', 'rear_left', 'rear_right'])`; h4: `pressBrakePedal(pedalPosition=1.0)`; h5: `startEngine(ignitionMode='START')`
- 매칭 개수: 정확=1, 부분=1; 미매칭 gold=['h2', 'h3', 'h4']
- 검토 플래그: 제공되지 않은 tool 사용: u1:checkFuelLevel; LLM judge override/rescue/downgrade 포함; 미매칭 gold hop: h2,h3,h4

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. checkFuelLevel(fuelAmount=15.0)` | False/False | 부분 | h1: `displayCarStatus({"_arg0": "fuel"})` (10) | h1: `displayCarStatus({"_arg0": "fuel"})` (10) | missing_tool_schema; argument_overlap:fuel;schema_invalid; hybrid_judge_rescue; judge=partial@0.78; judge_reason=The generated action semantically covers the fuel-status check, ... |
| `2. startEngine(ignitionMode="START")` | True/True | 정확 | h5: `startEngine({"ignitionMode": "START"})` (135) | h5: `startEngine({"ignitionMode": "START"})` (135) | schema_valid; exact_tool_name;parameter_overlap:ignitionMode;argument_overlap:ignitionmode,start;schema_valid |

## multi_turn_base_55 turn 1
- 목표: Since we are all set to go, could you quickly check the pressure of all the tires to ensure everything is safe for our journey?
- State view: `tree`
- Gold hop: h6: `check_tire_pressure()`
- 매칭 개수: 미매칭=2; 미매칭 gold=['h6']
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u1; 제공되지 않은 tool 사용: u2:checkTirePressure; 미매칭 gold hop: h6

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. displayCarStatus('tirePressure')` | True/False | 미매칭 | - | h6: `check_tire_pressure({})` (0) | positional_args_not_schema_checked; missing_required: option; schema_invalid; no_candidate_above_threshold |
| `2. checkTirePressure(showAll=True, tirePositions=['frontLeft', 'frontRight', 'rearLeft', 'rearRight'])` | False/False | 미매칭 | - | h6: `check_tire_pressure({})` (0) | missing_tool_schema; schema_invalid; no_candidate_above_threshold |

## multi_turn_base_55 turn 2
- 목표: The pressure seemed lower than expected. Let's open a ticket for 'Tire Pressure Issue', and detail it 'Urgent tire pressure issue.'. Given the urgency, classify this as the top priority to issue, where a higher score has more priority.
- State view: `tree`
- Gold hop: h7: `create_ticket(title='Tire Pressure Issue', description='Urgent tire pressure issue.', priority=5)`
- 매칭 개수: 정확=1; 미매칭 gold=[]

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. create_ticket(title="Tire Pressure Issue", description="Urgent tire pressure issue", priority="high")` | True/True | 정확 | h7: `create_ticket({"title": "Tire Pressure Issue", "description": "Urgent tire pressure iss...` (185) | h7: `create_ticket({"title": "Tire Pressure Issue", "description": "Urgent tire pressure iss...` (185) | schema_valid; exact_tool_name;parameter_overlap:description,priority,title;argument_overlap:description,issue,pressure,priority,tire,tire pressure issue,title,urgent;schema_valid |

## multi_turn_base_55 turn 3
- 목표: Apparently, I never got feedback on the tire pressure ticket I created. Can you fetch that ticket for me so I can review the current status?
- State view: `tree`
- Gold hop: h8: `get_ticket(ticket_id=2)`
- 매칭 개수: 부분=1; 미매칭 gold=[]
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u1; LLM judge override/rescue/downgrade 포함

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. get_ticket(id=2)` | True/False | 부분 | h8: `get_ticket({"ticket_id": 2})` (110) | h8: `get_ticket({"ticket_id": 2})` (110) | missing_required: ticket_id; unknown_parameters: id; exact_tool_name;argument_overlap:get_ticket;schema_invalid; hybrid_judge_override; judge=partial@0.92; judge_reason=The acti... |

## multi_turn_base_55 turn 4
- 목표: Great! They just gave me a call back. Now that I've checked the details, let's resolve the tire pressure ticket with an update stating 'Issue resolved!'.
- State view: `tree`
- Gold hop: h9: `resolve_ticket(ticket_id=2, resolution='Issue resolved!')`
- 매칭 개수: 미매칭=1; 미매칭 gold=['h9']
- 검토 플래그: 제공되지 않은 tool 사용: u1:update_ticket; 미매칭 gold hop: h9

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `2. update_ticket(ticket_id=2, title='Tire Pressure Issue', description='Issue resolved!')` | False/False | 미매칭 | - | h9: `resolve_ticket({"ticket_id": 2, "resolution": "Issue resolved!"})` (50) | missing_tool_schema; parameter_overlap:ticket_id;argument_overlap:issue,issue resolved!,resolved,ticket_id;schema_invalid; no_candidate_above_threshold |

## multi_turn_base_56 turn 0
- 목표: I'm setting off on a road trip and my departure point is sunny San Francisco. Could you determine the distance to Rivermist to help me plan my fuel stops on the way?
- State view: `tree`
- Gold hop: h1: `get_zipcode_based_on_city('San Francisco')`; h2: `get_zipcode_based_on_city('Rivermist')`; h3: `estimate_distance(cityA='94016', cityB='83214')`
- 매칭 개수: 부분=1, 미매칭=1; 미매칭 gold=['h1', 'h3']
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u1; schema 오류 또는 arg/param wrapper 문제: u2; 높은 점수 후보이나 primary 미매칭: u1->h1(130); LLM judge override/rescue/downgrade 포함; 미매칭 gold hop: h1,h3

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. get_zipcode_based_on_city(arg=city="Sun San Francisco")` | True/False | 미매칭 | - | h1: `get_zipcode_based_on_city({"_arg0": "San Francisco"})` (130) | syntax_error: invalid syntax; missing_required: city; exact_tool_name;argument_overlap:francisco,get_zipcode_based_on_city,san;schema_invalid; hybrid_judge_downgrade; judge=wron... |
| `2. get_zipcode_based_on_city(arg=city="Rivermist")` | True/False | 부분 | h2: `get_zipcode_based_on_city({"_arg0": "Rivermist"})` (110) | h2: `get_zipcode_based_on_city({"_arg0": "Rivermist"})` (110) | syntax_error: invalid syntax; missing_required: city; exact_tool_name;argument_overlap:rivermist;schema_invalid; hybrid_judge_override; judge=partial@0.94; judge_reason=The acti... |

## multi_turn_base_56 turn 1
- 목표: Before embarking on this journey, please top up my vehicle to end with 50 gallons of fuel.
- State view: `tree`
- Gold hop: h4: `displayCarStatus('fuel')`; h5: `fillFuelTank(fuelAmount=40)`
- 매칭 개수: 미매칭=3; 미매칭 gold=['h4', 'h5']
- 검토 플래그: 높은 점수 후보이나 primary 미매칭: u2->h5(125); LLM judge override/rescue/downgrade 포함; 미매칭 gold hop: h4,h5

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. startEngine(ignitionMode="STOP")` | True/True | 미매칭 | - | h4: `displayCarStatus({"_arg0": "fuel"})` (15) | schema_valid; argument_overlap:fuel;schema_valid; no_candidate_above_threshold |
| `2. fillFuelTank(fuelAmount=50.0)` | True/True | 미매칭 | - | h5: `fillFuelTank({"fuelAmount": 40})` (125) | schema_valid; exact_tool_name;parameter_overlap:fuelAmount;argument_overlap:fuelamount;schema_valid; hybrid_judge_downgrade; judge=wrong@0.98; judge_reason=Same tool, but the co... |
| `3. startEngine(ignitionMode="RESTART")` | True/True | 미매칭 | - | h4: `displayCarStatus({"_arg0": "fuel"})` (5) | schema_valid; no_candidate_above_threshold |

## multi_turn_base_56 turn 2
- 목표: Please start the engine to prepare for our travel. Ensure that the car is locked and everything is secure for a seamless start.
- State view: `tree`
- Gold hop: h6: `lockDoors(unlock=False, door=['driver', 'passenger', 'rear_left', 'rear_right'])`; h7: `pressBrakePedal(pedalPosition=1.0)`; h8: `startEngine(ignitionMode='START')`
- 매칭 개수: 정확=1, 미매칭=2; 미매칭 gold=['h6', 'h7']
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u1; schema 오류 또는 arg/param wrapper 문제: u2; 미매칭 gold hop: h6,h7

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. displayCarStatus('doors')` | True/False | 미매칭 | - | h6: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rear_right"]})` (0) | positional_args_not_schema_checked; missing_required: option; schema_invalid; no_candidate_above_threshold |
| `2. displayCarStatus('engine')` | True/False | 미매칭 | - | h6: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rear_right"]})` (0) | positional_args_not_schema_checked; missing_required: option; schema_invalid; no_candidate_above_threshold |
| `3. startEngine(ignitionMode='START')` | True/True | 정확 | h8: `startEngine({"ignitionMode": "START"})` (135) | h8: `startEngine({"ignitionMode": "START"})` (135) | schema_valid; exact_tool_name;parameter_overlap:ignitionMode;argument_overlap:ignitionmode,start;schema_valid |

## multi_turn_base_57 turn 0
- 목표: I've been thinking of visiting Autumnville for a while now, but I'm not sure how far it is from here in Crescent Hollow. Can you help me figure this out so I can plan my trip accordingly?
- State view: `tree`
- Gold hop: h1: `get_zipcode_based_on_city('Crescent Hollow')`; h2: `get_zipcode_based_on_city('Autumnville')`; h3: `estimate_distance(cityA='69238', cityB='51479')`
- 매칭 개수: 미매칭=4; 미매칭 gold=['h1', 'h2', 'h3']
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u4; 미매칭 gold hop: h1,h2,h3

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. si_unit_conversion(value=100.0, unit_in="miles", unit_out="km")` | True/True | 미매칭 | - | h1: `get_zipcode_based_on_city({"_arg0": "Crescent Hollow"})` (25) | schema_valid; argument_overlap:crescent,hollow;schema_valid; no_candidate_above_threshold |
| `2. si_unit_conversion(value=100.0, unit_in="km", unit_out="km")` | True/True | 미매칭 | - | h1: `get_zipcode_based_on_city({"_arg0": "Crescent Hollow"})` (5) | schema_valid; no_candidate_above_threshold |
| `3. si_unit_conversion(value=100.0, unit_in="km", unit_out="km")` | True/True | 미매칭 | - | h1: `get_zipcode_based_on_city({"_arg0": "Crescent Hollow"})` (5) | schema_valid; no_candidate_above_threshold |
| `4. si_unit_conversion(value=$3.result, unit_in="km", unit_out="km)` | True/False | 미매칭 | - | h1: `get_zipcode_based_on_city({"_arg0": "Crescent Hollow"})` (0) | syntax_error: unterminated string literal (detected at line 1); missing_required: unit_in, unit_out, value; schema_invalid;unresolved_input; no_candidate_above_threshold |

## multi_turn_base_57 turn 1
- 목표: Oh, and by the way, there's something else I need help with. I want to calculate the logarithm of the distance you've just told me about, considering a base 10 with a precision of 5 digits. Could you provide me with this value as well?
- State view: `tree`
- Gold hop: h4: `logarithm(value=630.0, base=10, precision=5)`
- 매칭 개수: 정확=2; 미매칭 gold=[]
- 검토 플래그: LLM judge override/rescue/downgrade 포함

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. logarithm(value=630.0, base=10, precision=5)` | True/True | 정확 | h4: `logarithm({"value": 630.0, "base": 10, "precision": 5})` (185) | h4: `logarithm({"value": 630.0, "base": 10, "precision": 5})` (185) | schema_valid; exact_tool_name;parameter_overlap:base,precision,value;argument_overlap:10,630.0,base,logarithm,precision,value;schema_valid; hybrid_judge_rescue; judge=exact@1; j... |
| `2. logarithm(value=630.0, base=10, precision=5)` | True/True | 정확 | h4: `logarithm({"value": 630.0, "base": 10, "precision": 5})` (185) | h4: `logarithm({"value": 630.0, "base": 10, "precision": 5})` (185) | schema_valid; exact_tool_name;parameter_overlap:base,precision,value;argument_overlap:10,630.0,base,precision,value;schema_valid; duplicate_primary_match |

## multi_turn_base_59 turn 0
- 목표: I recently moved to San Francisco and I’m planning a trip to Rivermist. How far apart are these places? I'd like to gauge the distance before setting off on this adventure.
- State view: `tree`
- Gold hop: h1: `get_zipcode_based_on_city('San Francisco')`; h2: `get_zipcode_based_on_city('Rivermist')`; h3: `estimate_distance(cityA='94016', cityB='83214')`
- 매칭 개수: 미매칭=5; 미매칭 gold=['h1', 'h2', 'h3']
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u5; 미매칭 gold hop: h1,h2,h3

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. si_unit_conversion(value=50.0, unit_in="miles", unit_out="km")` | True/True | 미매칭 | - | h1: `get_zipcode_based_on_city({"_arg0": "San Francisco"})` (25) | schema_valid; argument_overlap:francisco,san;schema_valid; no_candidate_above_threshold |
| `2. si_unit_conversion(value=50.0, unit_in="miles", unit_out="km")` | True/True | 미매칭 | - | h1: `get_zipcode_based_on_city({"_arg0": "San Francisco"})` (5) | schema_valid; no_candidate_above_threshold |
| `3. si_unit_conversion(value=50.0, unit_in="km", unit_out="km")` | True/True | 미매칭 | - | h1: `get_zipcode_based_on_city({"_arg0": "San Francisco"})` (5) | schema_valid; no_candidate_above_threshold |
| `4. si_unit_conversion(value=50.0, unit_in="km", unit_out="km")` | True/True | 미매칭 | - | h1: `get_zipcode_based_on_city({"_arg0": "San Francisco"})` (5) | schema_valid; no_candidate_above_threshold |
| `5. sum_values(value=$4.result)` | True/False | 미매칭 | - | h1: `get_zipcode_based_on_city({"_arg0": "San Francisco"})` (0) | missing_required: numbers; unknown_parameters: value; schema_invalid;unresolved_input; no_candidate_above_threshold |

## multi_turn_base_59 turn 1
- 목표: Now that I have the distance sorted, I'm considering the fuel situation. What's the current level of gasoline I have in liters?
- State view: `tree`
- Gold hop: h4: `displayCarStatus(option='fuel')`; h5: `gallon_to_liter(gallon=10)`
- 매칭 개수: 의미=1; 미매칭 gold=['h5']
- 검토 플래그: 제공되지 않은 tool 사용: u1:get_vehicle_status; LLM judge override/rescue/downgrade 포함; 미매칭 gold hop: h5

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. get_vehicle_status(field='fuelLevel')` | False/False | 의미 | h4: `displayCarStatus({"option": "fuel"})` (10) | h4: `displayCarStatus({"option": "fuel"})` (10) | missing_tool_schema; argument_overlap:fuel;schema_invalid; hybrid_judge_rescue; judge=semantic@0.86; judge_reason=The generated action uses a non-gold/synonym status getter, but... |

## multi_turn_base_59 turn 2
- 목표: With the liters in mind, I'll need to top up my vehicle’s tank. Please go ahead and fill up the tank before I hit the road.
- State view: `tree`
- Gold hop: h6: `fillFuelTank(fuelAmount=40)`
- 매칭 개수: 미매칭=2; 미매칭 gold=['h6']
- 검토 플래그: 제공되지 않은 tool 사용: u2:updateFuelLevel; 미매칭 gold hop: h6

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. displayCarStatus(option='fuel')` | True/True | 미매칭 | - | h6: `fillFuelTank({"fuelAmount": 40})` (5) | schema_valid; no_candidate_above_threshold |
| `2. updateFuelLevel(fuelAmount=50.0)` | False/False | 미매칭 | - | h6: `fillFuelTank({"fuelAmount": 40})` (20) | missing_tool_schema; parameter_overlap:fuelAmount;argument_overlap:fuelamount;schema_invalid; no_candidate_above_threshold |

## multi_turn_base_59 turn 3
- 목표: As the journey is about to begin, could you kindly engage the 'START' ignition mode to ready the vehicle? I want to ensure everything's in perfect working order before I drive off.
- State view: `tree`
- Gold hop: h7: `lockDoors(unlock=False, door=['driver', 'passenger', 'rear_left', 'rear_right'])`; h8: `pressBrakePedal(pedalPosition=1.0)`; h9: `startEngine(ignitionMode='START')`
- 매칭 개수: 부분=1, 미매칭=2; 미매칭 gold=['h7', 'h8']
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u1; LLM judge override/rescue/downgrade 포함; 미매칭 gold hop: h7,h8

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. startEngine(operation='start')` | True/False | 부분 | h9: `startEngine({"ignitionMode": "START"})` (120) | h9: `startEngine({"ignitionMode": "START"})` (120) | missing_required: ignitionMode; unknown_parameters: operation; exact_tool_name;argument_overlap:start,startengine;schema_invalid; hybrid_judge_override; judge=partial@0.86; judg... |
| `2. displayCarStatus(option='engine')` | True/True | 미매칭 | - | h7: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rear_right"]})` (5) | schema_valid; no_candidate_above_threshold |
| `3. displayCarStatus(option='engine')` | True/True | 미매칭 | - | h7: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rear_right"]})` (5) | schema_valid; no_candidate_above_threshold |

## multi_turn_base_59 turn 4
- 목표: Finally, I'm analyzing mileage statistics and need the logarithm of the distance to the base the previous fuel value, computed to a precision of 10. Use base of 20. This will help with assessing the fuel efficiency patterns.
- State view: `tree`
- Gold hop: h10: `logarithm(value=980.0, base=20, precision=10)`
- 매칭 개수: 정확=1, 미매칭=3; 미매칭 gold=[]

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. displayCarStatus(option='fuel')` | True/True | 미매칭 | - | h10: `logarithm({"value": 980.0, "base": 20, "precision": 10})` (5) | schema_valid; no_candidate_above_threshold |
| `2. gallon_to_liter(gallon=50)` | True/True | 미매칭 | - | h10: `logarithm({"value": 980.0, "base": 20, "precision": 10})` (5) | schema_valid; no_candidate_above_threshold |
| `3. estimate_distance(cityA='San Francisco', cityB='83214')` | True/True | 미매칭 | - | h10: `logarithm({"value": 980.0, "base": 20, "precision": 10})` (5) | schema_valid; no_candidate_above_threshold |
| `4. logarithm(value=980.0, base=20, precision=10)` | True/True | 정확 | h10: `logarithm({"value": 980.0, "base": 20, "precision": 10})` (185) | h10: `logarithm({"value": 980.0, "base": 20, "precision": 10})` (185) | schema_valid; exact_tool_name;parameter_overlap:base,precision,value;argument_overlap:10,20,980.0,base,precision,value;schema_valid |

## multi_turn_base_62 turn 0
- 목표: I'm currently in Rivermist planning a trip to Stonebrook. Could you provide an estimate of the distance and forward this info to my cousin Bob via text, in the format 'The distance from Rivermist to Stonebrook is xxx km.', where xxx is replaced by the distance value, in one de...
- State view: `tree`
- Gold hop: h1: `get_zipcode_based_on_city('Rivermist')`; h2: `get_zipcode_based_on_city('Stonebrook')`; h3: `estimate_distance(cityA='83214', cityB='74532')`; h4: `send_message(receiver_id='USR002', message='The distance from Rivermist to Stonebrook is 750.0 km.')`
- 매칭 개수: 부분=1, 미매칭=3; 미매칭 gold=['h1', 'h2', 'h3']
- 검토 플래그: 제공되지 않은 tool 사용: u1:get_navigation; 제공되지 않은 tool 사용: u2:get_navigation; 제공되지 않은 tool 사용: u3:format_message; schema 오류 또는 arg/param wrapper 문제: u4; LLM judge override/rescue/downgrade 포함; 미매칭 gold hop: h1,h2,h3

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. get_navigation(arg={"destination": "Stonebrook"})` | False/False | 미매칭 | - | h4: `send_message({"receiver_id": "USR002", "message": "The distance from Rivermist to Stone...` (30) | missing_tool_schema; argument_overlap:distance,rivermist,stonebrook;schema_invalid; no_candidate_above_threshold |
| `2. get_navigation(arg={"destination": "Rivermist"})` | False/False | 미매칭 | - | h1: `get_zipcode_based_on_city({"_arg0": "Rivermist"})` (10) | missing_tool_schema; argument_overlap:rivermist;schema_invalid; no_candidate_above_threshold |
| `3. format_message(arg={"message": "The distance from Rivermist to Stonebrook is $distance km.", "template": "The dist...` | False/False | 미매칭 | - | h4: `send_message({"receiver_id": "USR002", "message": "The distance from Rivermist to Stone...` (50) | missing_tool_schema; argument_overlap:distance,km.,message,rivermist,stonebrook;schema_invalid; no_candidate_above_threshold |
| `4. send_message(arg={"user_name": "Bob", "user_id": "USR002"})` | True/False | 부분 | h4: `send_message({"receiver_id": "USR002", "message": "The distance from Rivermist to Stone...` (110) | h4: `send_message({"receiver_id": "USR002", "message": "The distance from Rivermist to Stone...` (110) | missing_required: message, receiver_id; unknown_parameters: arg; exact_tool_name;argument_overlap:usr002;schema_invalid; hybrid_judge_confirm; judge=partial@0.91; judge_reason=T... |

## multi_turn_base_62 turn 1
- 목표: As I set off on my drive, I need you to verify that all the doors on my car are securely locked, please.
- State view: `tree`
- Gold hop: h5: `lockDoors(unlock=False, door=['driver', 'passenger', 'rear_left', 'rear_right'])`
- 매칭 개수: 부분=1, 미매칭=1; 미매칭 gold=[]
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u1; 제공되지 않은 tool 사용: u2:get_doorStatus; LLM judge override/rescue/downgrade 포함

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. lockDoors(lockStatus={"driver": "locked", "passenger": "locked", "rear_left": "locked", "rear_right": "locked"})` | True/False | 부분 | h5: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rear_right"]})` (140) | h5: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rear_right"]})` (140) | missing_required: door, unlock; unknown_parameters: lockStatus; exact_tool_name;argument_overlap:driver,passenger,rear_left,rear_right;schema_invalid; hybrid_judge_override; jud... |
| `2. get_doorStatus(lockStatus="locked"})` | False/False | 미매칭 | - | h5: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rear_right"]})` (0) | missing_tool_schema; schema_invalid; no_candidate_above_threshold |

## multi_turn_base_62 turn 2
- 목표: After confirming the security of the vehicle, could you initiate the engine so I can check the fuel level?
- State view: `tree`
- Gold hop: h6: `pressBrakePedal(pedalPosition=1.0)`; h7: `startEngine(ignitionMode='START')`
- 매칭 개수: 정확=1; 미매칭 gold=['h6']
- 검토 플래그: 미매칭 gold hop: h6

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. startEngine(ignitionMode='AUTO')` | True/True | 정확 | h7: `startEngine({"ignitionMode": "START"})` (145) | h7: `startEngine({"ignitionMode": "START"})` (145) | schema_valid; exact_tool_name;parameter_overlap:ignitionMode;argument_overlap:ignitionmode,start,startengine;schema_valid |

## multi_turn_base_62 turn 3
- 목표: Also, at your earliest convenience, can you show me all the messages I have send so far?
- State view: `tree`
- Gold hop: h8: `view_messages_sent()`
- 매칭 개수: 미매칭=1; 미매칭 gold=['h8']
- 검토 플래그: 미매칭 gold hop: h8

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. send_message(receiver_id='USR002', message='The distance from Rivermist to Stonebrook is 750.0 km.')` | True/True | 미매칭 | - | h8: `view_messages_sent({})` (5) | schema_valid; no_candidate_above_threshold |

## multi_turn_base_67 turn 0
- 목표: Will you estimate the distance between San Francisco and Silverpine for me?
- State view: `tree`
- Gold hop: h1: `get_zipcode_based_on_city('San Francisco')`; h2: `get_zipcode_based_on_city('Silverpine')`; h3: `estimate_distance(cityA='94016', cityB='62947')`
- 매칭 개수: 부분=4, 미매칭=1; 미매칭 gold=['h3']
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u1; schema 오류 또는 arg/param wrapper 문제: u2; 제공되지 않은 tool 사용: u3:calculate_distance_between_cities; schema 오류 또는 arg/param wrapper 문제: u4; schema 오류 또는 arg/param wrapper 문제: u5; LLM judge override/rescue/downgrade 포함; 미매칭 gold hop: h3

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. get_zipcode_based_on_city(arg={"city": "San Francisco"})` | True/False | 부분 | h1: `get_zipcode_based_on_city({"_arg0": "San Francisco"})` (130) | h1: `get_zipcode_based_on_city({"_arg0": "San Francisco"})` (130) | missing_required: city; unknown_parameters: arg; exact_tool_name;argument_overlap:francisco,san,san francisco;schema_invalid; hybrid_judge_rescue; judge=partial@0.93; judge_reas... |
| `2. get_zipcode_based_on_city(arg={"city": "Silverpine"})` | True/False | 부분 | h2: `get_zipcode_based_on_city({"_arg0": "Silverpine"})` (110) | h2: `get_zipcode_based_on_city({"_arg0": "Silverpine"})` (110) | missing_required: city; unknown_parameters: arg; exact_tool_name;argument_overlap:silverpine;schema_invalid; hybrid_judge_rescue; judge=partial@0.95; judge_reason=The generated ... |
| `3. calculate_distance_between_cities(arg={"city1": "San Francisco", "city2": "Silverpine"})` | False/False | 미매칭 | - | h1: `get_zipcode_based_on_city({"_arg0": "San Francisco"})` (30) | missing_tool_schema; argument_overlap:francisco,san,san francisco;schema_invalid; no_candidate_above_threshold |
| `4. get_zipcode_based_on_city(arg={"city": "San Francisco"})` | True/False | 부분 | h1: `get_zipcode_based_on_city({"_arg0": "San Francisco"})` (130) | h1: `get_zipcode_based_on_city({"_arg0": "San Francisco"})` (130) | missing_required: city; unknown_parameters: arg; exact_tool_name;argument_overlap:francisco,san,san francisco;schema_invalid; hybrid_judge_override; judge=partial@0.94; judge_re... |
| `5. get_zipcode_based_on_city(arg={"city": "Silverpine"})` | True/False | 부분 | h2: `get_zipcode_based_on_city({"_arg0": "Silverpine"})` (110) | h2: `get_zipcode_based_on_city({"_arg0": "Silverpine"})` (110) | missing_required: city; unknown_parameters: arg; exact_tool_name;argument_overlap:silverpine;schema_invalid; hybrid_judge_override; judge=partial@0.91; judge_reason=The generate... |

## multi_turn_base_67 turn 1
- 목표: I need that info to check if my vehicle can cover the distance without refueling.
- State view: `tree`
- Gold hop: h4: `estimate_drive_feasibility_by_mileage(distance=780.0)`
- 매칭 개수: 미매칭=4; 미매칭 gold=['h4']
- 검토 플래그: 미매칭 gold hop: h4

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. setHeadlights(mode="off")` | True/True | 미매칭 | - | h4: `estimate_drive_feasibility_by_mileage({"distance": 780.0})` (15) | schema_valid; argument_overlap:distance;schema_valid; no_candidate_above_threshold |
| `2. setHeadlights(mode="on")` | True/True | 미매칭 | - | h4: `estimate_drive_feasibility_by_mileage({"distance": 780.0})` (5) | schema_valid; no_candidate_above_threshold |
| `3. setHeadlights(mode="off")` | True/True | 미매칭 | - | h4: `estimate_drive_feasibility_by_mileage({"distance": 780.0})` (5) | schema_valid; no_candidate_above_threshold |
| `4. setHeadlights(mode="on")` | True/True | 미매칭 | - | h4: `estimate_drive_feasibility_by_mileage({"distance": 780.0})` (5) | schema_valid; no_candidate_above_threshold |

## multi_turn_base_67 turn 2
- 목표: In case it can't, just fill out the fuel tank completely.
- State view: `tree`
- Gold hop: h5: `fillFuelTank(fuelAmount=39.5)`
- 매칭 개수: 미매칭=3; 미매칭 gold=['h5']
- 검토 플래그: 높은 점수 후보이나 primary 미매칭: u2->h5(125); LLM judge override/rescue/downgrade 포함; 미매칭 gold hop: h5

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. estimate_drive_feasibility_by_mileage(distance=780.0)` | True/True | 미매칭 | - | h5: `fillFuelTank({"fuelAmount": 39.5})` (5) | schema_valid; no_candidate_above_threshold |
| `2. fillFuelTank(fuelAmount=20.0)` | True/True | 미매칭 | - | h5: `fillFuelTank({"fuelAmount": 39.5})` (125) | schema_valid; exact_tool_name;parameter_overlap:fuelAmount;argument_overlap:fuelamount;schema_valid; hybrid_judge_downgrade; judge=wrong@0.98; judge_reason=Same tool, but the ge... |
| `3. setHeadlights(mode='on')` | True/True | 미매칭 | - | h5: `fillFuelTank({"fuelAmount": 39.5})` (5) | schema_valid; no_candidate_above_threshold |

## multi_turn_base_67 turn 3
- 목표: Turn on my vehicle's engine in 'START' mode.
- State view: `tree`
- Gold hop: h6: `lockDoors(unlock=False, door=['driver', 'passenger', 'rear_left', 'rear_right'])`; h7: `pressBrakePedal(pedalPosition=1.0)`; h8: `startEngine(ignitionMode='START')`
- 매칭 개수: 정확=1, 미매칭=1; 미매칭 gold=['h6', 'h7']
- 검토 플래그: 제공되지 않은 tool 사용: u1:get_engine_state; 미매칭 gold hop: h6,h7

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. get_engine_state()` | False/False | 미매칭 | - | h8: `startEngine({"ignitionMode": "START"})` (30) | missing_tool_schema; argument_overlap:ignitionmode,start,startengine;schema_invalid; no_candidate_above_threshold |
| `2. startEngine(ignitionMode='START')` | True/True | 정확 | h8: `startEngine({"ignitionMode": "START"})` (135) | h8: `startEngine({"ignitionMode": "START"})` (135) | schema_valid; exact_tool_name;parameter_overlap:ignitionMode;argument_overlap:ignitionmode,start;schema_valid |

## multi_turn_base_70 turn 0
- 목표: Ensure the fuel tank is replenished adequately by adding 38 liters of gasoline so that we're well-prepared for the lengthy voyage ahead. Only fill with interger amount for volumn; round when not integer. Once fueled, proceed to start the engine confidently with the ignition mo...
- State view: `tree`
- Gold hop: h1: `liter_to_gallon(liter=38)`; h2: `fillFuelTank(fuelAmount=10)`; h3: `activateParkingBrake(mode='engage')`; h4: `lockDoors(unlock=False, door=['driver', 'passenger', 'rear_left', 'rear_right'])`; h5: `pressBrakePedal(pedalPosition=1.0)`; h6: `startEngine(ignitionMode='START')`
- 매칭 개수: 부분=1, 미매칭=1; 미매칭 gold=['h1', 'h2', 'h3', 'h4', 'h5']
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u1; schema 오류 또는 arg/param wrapper 문제: u2; 높은 점수 후보이나 primary 미매칭: u1->h2(110); LLM judge override/rescue/downgrade 포함; 미매칭 gold hop: h1,h2,h3,h4,h5

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. fillFuelTank(param={"fuelAmount": 38.0})` | True/False | 미매칭 | - | h2: `fillFuelTank({"fuelAmount": 10})` (110) | missing_required: fuelAmount; unknown_parameters: param; exact_tool_name;argument_overlap:fuelamount;schema_invalid; hybrid_judge_downgrade; judge=wrong@0.96; judge_reason=Same ... |
| `2. startEngine(param={"ignitionMode": "START"})` | True/False | 부분 | h6: `startEngine({"ignitionMode": "START"})` (120) | h6: `startEngine({"ignitionMode": "START"})` (120) | missing_required: ignitionMode; unknown_parameters: param; exact_tool_name;argument_overlap:ignitionmode,start;schema_invalid; hybrid_judge_override; judge=partial@0.94; judge_r... |

## multi_turn_base_70 turn 1
- 목표: As we gear up for our adventure, it’s wise to confirm that each tire is inflated to a stable 32 PSI. Should any of the tires fall short, chart a course to the nearest tire service center to have this rectified.
- State view: `tree`
- Gold hop: h7: `check_tire_pressure()`; h8: `find_nearest_tire_shop()`; h9: `set_navigation(destination='456 Oakwood Avenue, Rivermist, 83214')`
- 매칭 개수: 미매칭=1; 미매칭 gold=['h7', 'h8', 'h9']
- 검토 플래그: 제공되지 않은 tool 사용: u1:checkTirePressure; 미매칭 gold hop: h7,h8,h9

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. checkTirePressure(frontLeftTirePressure=32, frontRightTirePressure=32, rearLeftTirePressure=32, rearRightTirePress...` | False/False | 미매칭 | - | h7: `check_tire_pressure({})` (0) | missing_tool_schema; schema_invalid; no_candidate_above_threshold |

## multi_turn_base_71 turn 0
- 목표: Using my vehicle's system, estimate the distance between Rivermist and Stonebrook.
- State view: `tree`
- Gold hop: h1: `get_zipcode_based_on_city('Rivermist')`; h2: `get_zipcode_based_on_city('Stonebrook')`; h3: `estimate_distance(cityA='83214', cityB='74532')`
- 매칭 개수: 부분=3, 미매칭=1; 미매칭 gold=['h3']
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u1; schema 오류 또는 arg/param wrapper 문제: u2; schema 오류 또는 arg/param wrapper 문제: u3; schema 오류 또는 arg/param wrapper 문제: u4; LLM judge override/rescue/downgrade 포함; 미매칭 gold hop: h3

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. get_zipcode_based_on_city(arg={"city": "Rivermist"})` | True/False | 부분 | h1: `get_zipcode_based_on_city({"_arg0": "Rivermist"})` (110) | h1: `get_zipcode_based_on_city({"_arg0": "Rivermist"})` (110) | missing_required: city; unknown_parameters: arg; exact_tool_name;argument_overlap:rivermist;schema_invalid; hybrid_judge_override; judge=partial@0.92; judge_reason=The generated... |
| `2. get_zipcode_based_on_city(arg={"city": "Stonebrook"})` | True/False | 부분 | h2: `get_zipcode_based_on_city({"_arg0": "Stonebrook"})` (110) | h2: `get_zipcode_based_on_city({"_arg0": "Stonebrook"})` (110) | missing_required: city; unknown_parameters: arg; exact_tool_name;argument_overlap:stonebrook;schema_invalid; hybrid_judge_rescue; judge=partial@0.93; judge_reason=The generated ... |
| `3. set_navigation(arg={"destination": "Rivermist, Stonebrook"})` | True/False | 미매칭 | - | h1: `get_zipcode_based_on_city({"_arg0": "Rivermist"})` (10) | missing_required: destination; unknown_parameters: arg; argument_overlap:rivermist;schema_invalid; no_candidate_above_threshold |
| `4. get_zipcode_based_on_city(arg={"city": "Rivermist, Stonebrook"})` | True/False | 부분 | h2: `get_zipcode_based_on_city({"_arg0": "Stonebrook"})` (110) | h1: `get_zipcode_based_on_city({"_arg0": "Rivermist"})` (110) | missing_required: city; unknown_parameters: arg; exact_tool_name;argument_overlap:rivermist;schema_invalid; hybrid_judge_confirm; judge=partial@0.86; judge_reason=The generated ... |

## multi_turn_base_71 turn 1
- 목표: Assess if my vehicle's current mileage will suffice for the distance calculated. You don't need to re-fill, I just want to know.
- State view: `tree`
- Gold hop: h4: `estimate_drive_feasibility_by_mileage(distance=750.0)`
- 매칭 개수: 미매칭=3; 미매칭 gold=['h4']
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u1; schema 오류 또는 arg/param wrapper 문제: u2; 미매칭 gold hop: h4

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. get_zipcode_based_on_city('Rivermist')` | True/False | 미매칭 | - | h4: `estimate_drive_feasibility_by_mileage({"distance": 750.0})` (10) | positional_args_not_schema_checked; missing_required: city; argument_overlap:distance;schema_invalid; no_candidate_above_threshold |
| `2. get_zipcode_based_on_city('Stonebrook')` | True/False | 미매칭 | - | h4: `estimate_drive_feasibility_by_mileage({"distance": 750.0})` (0) | positional_args_not_schema_checked; missing_required: city; schema_invalid; no_candidate_above_threshold |
| `3. estimate_distance(cityA='83214', cityB='74532')` | True/True | 미매칭 | - | h4: `estimate_drive_feasibility_by_mileage({"distance": 750.0})` (5) | schema_valid; no_candidate_above_threshold |

## multi_turn_base_71 turn 2
- 목표: Fill the fuel tank to completely full.
- State view: `tree`
- Gold hop: h5: `fillFuelTank(fuelAmount=45.0)`
- 매칭 개수: 미매칭=3; 미매칭 gold=['h5']
- 검토 플래그: 높은 점수 후보이나 primary 미매칭: u1->h5(135); LLM judge override/rescue/downgrade 포함; 미매칭 gold hop: h5

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. fillFuelTank(fuelAmount=20.0)` | True/True | 미매칭 | - | h5: `fillFuelTank({"fuelAmount": 45.0})` (135) | schema_valid; exact_tool_name;parameter_overlap:fuelAmount;argument_overlap:fillfueltank,fuelamount;schema_valid; hybrid_judge_downgrade; judge=wrong@0.96; judge_reason=Correct ... |
| `2. startEngine(ignitionMode='START')` | True/True | 미매칭 | - | h5: `fillFuelTank({"fuelAmount": 45.0})` (5) | schema_valid; no_candidate_above_threshold |
| `3. startEngine(ignitionMode='STOP')` | True/True | 미매칭 | - | h5: `fillFuelTank({"fuelAmount": 45.0})` (5) | schema_valid; no_candidate_above_threshold |

## multi_turn_base_71 turn 3
- 목표: With the vehicle secured, start the engine for our prepared journey.
- State view: `tree`
- Gold hop: h6: `lockDoors(unlock=False, door=['driver', 'passenger', 'rear_left', 'rear_right'])`; h7: `pressBrakePedal(pedalPosition=1.0)`; h8: `startEngine(ignitionMode='START')`
- 매칭 개수: 정확=1, 미매칭=1; 미매칭 gold=['h6', 'h7']
- 검토 플래그: 미매칭 gold hop: h6,h7

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. setHeadlights(mode="on")` | True/True | 미매칭 | - | h8: `startEngine({"ignitionMode": "START"})` (25) | schema_valid; argument_overlap:start,startengine;schema_valid; no_candidate_above_threshold |
| `2. startEngine(ignitionMode="START")` | True/True | 정확 | h8: `startEngine({"ignitionMode": "START"})` (135) | h8: `startEngine({"ignitionMode": "START"})` (135) | schema_valid; exact_tool_name;parameter_overlap:ignitionMode;argument_overlap:ignitionmode,start;schema_valid |

## multi_turn_base_71 turn 4
- 목표: Set navigation directly to Crescent Hollow, Spring, TX for a smooth ride without detours.
- State view: `tree`
- Gold hop: h9: `set_navigation(destination='Crescent Hollow, Spring, TX')`
- 매칭 개수: 정확=2; 미매칭 gold=[]
- 검토 플래그: LLM judge override/rescue/downgrade 포함

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. set_navigation(destination='Crescent Hollow, Spring, TX')` | True/True | 정확 | h9: `set_navigation({"destination": "Crescent Hollow, Spring, TX"})` (165) | h9: `set_navigation({"destination": "Crescent Hollow, Spring, TX"})` (165) | schema_valid; exact_tool_name;parameter_overlap:destination;argument_overlap:crescent,crescent hollow, spring, tx,destination,hollow,set_navigation,spring,tx;schema_valid; hybri... |
| `2. set_navigation(destination='Crescent Hollow, Spring, TX')` | True/True | 정확 | h9: `set_navigation({"destination": "Crescent Hollow, Spring, TX"})` (165) | h9: `set_navigation({"destination": "Crescent Hollow, Spring, TX"})` (165) | schema_valid; exact_tool_name;parameter_overlap:destination;argument_overlap:crescent,crescent hollow, spring, tx,destination,hollow,spring,tx;schema_valid; duplicate_primary_match |

## multi_turn_base_86 turn 0
- 목표: Lock all doors and engage the parking brake, then start the vehicle's engine in preparation for a trip. Afterward, check if our tire pressure condition is safe to proceed.
- State view: `tree`
- Gold hop: h1: `lockDoors(unlock=False, door=['driver', 'passenger', 'rear_left', 'rear_right'])`; h2: `activateParkingBrake(mode='engage')`; h3: `pressBrakePedal(pedalPosition=1.0)`; h4: `startEngine(ignitionMode='START')`; h5: `check_tire_pressure()`
- 매칭 개수: 정확=1, 미매칭=3; 미매칭 gold=['h1', 'h2', 'h3', 'h5']
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u1; schema 오류 또는 arg/param wrapper 문제: u2; 미매칭 gold hop: h1,h2,h3,h5

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. setHeadlights(headLightStatus="on")` | True/False | 미매칭 | - | h2: `activateParkingBrake({"mode": "engage"})` (10) | missing_required: mode; unknown_parameters: headLightStatus; argument_overlap:engage;schema_invalid; no_candidate_above_threshold |
| `2. setHeadlights(headLightStatus="on")` | True/False | 미매칭 | - | h1: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rear_right"]})` (0) | missing_required: mode; unknown_parameters: headLightStatus; schema_invalid; no_candidate_above_threshold |
| `3. setHeadlights(mode="on")` | True/True | 미매칭 | - | h2: `activateParkingBrake({"mode": "engage"})` (25) | schema_valid; parameter_overlap:mode;argument_overlap:mode;schema_valid; no_candidate_above_threshold |
| `4. startEngine(ignitionMode="START")` | True/True | 정확 | h4: `startEngine({"ignitionMode": "START"})` (135) | h4: `startEngine({"ignitionMode": "START"})` (135) | schema_valid; exact_tool_name;parameter_overlap:ignitionMode;argument_overlap:ignitionmode,start;schema_valid |

## multi_turn_base_86 turn 1
- 목표: The tire pressure seems worrying, kindly find the nearest tire shop to address the issue and set our navigation to that location.
- State view: `tree`
- Gold hop: h6: `find_nearest_tire_shop()`; h7: `set_navigation(destination='456 Oakwood Avenue, Rivermist, 83214')`
- 매칭 개수: 정확=1, 미매칭=1; 미매칭 gold=['h6']
- 검토 플래그: 미매칭 gold hop: h6

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. setCruiseControl(speed=60, activate=True, distanceToNextVehicle=10.0)` | True/True | 미매칭 | - | h6: `find_nearest_tire_shop({})` (5) | schema_valid; no_candidate_above_threshold |
| `2. set_navigation(destination="nearest tire shop")` | True/True | 정확 | h7: `set_navigation({"destination": "456 Oakwood Avenue, Rivermist, 83214"})` (125) | h7: `set_navigation({"destination": "456 Oakwood Avenue, Rivermist, 83214"})` (125) | schema_valid; exact_tool_name;parameter_overlap:destination;argument_overlap:destination;schema_valid |

## multi_turn_base_86 turn 2
- 목표: I have the tire issue fixed. Thinking aloud, since it's been a successful start to this journey, I'd like to send a thank you tweet 'Thank you to our vehicle for a smooth start!' about our vehicle with a few hashtags '#Journey, #SmoothRide, #Grateful' added.
- State view: `tree`
- Gold hop: h8: `post_tweet(content='Thank you to our vehicle for a smooth start!', tags=['#Journey', '#SmoothRide', '#Grateful'])`
- 매칭 개수: 부분=1; 미매칭 gold=[]
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u1; LLM judge override/rescue/downgrade 포함

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. post_tweet(content="Thank you to our vehicle for a smooth start!", hashtags=[["#Journey", "#SmoothRide", "#Gratefu...` | True/False | 부분 | h8: `post_tweet({"content": "Thank you to our vehicle for a smooth start!", "tags": ["#Journ...` (160) | h8: `post_tweet({"content": "Thank you to our vehicle for a smooth start!", "tags": ["#Journ...` (160) | unknown_parameters: hashtags; exact_tool_name;parameter_overlap:content;argument_overlap:#grateful,#journey,#smoothride,content,grateful,journey,our,smooth;schema_invalid; hybri... |

## multi_turn_base_87 turn 0
- 목표: As I gear up for another delightful journey exploring the captivating waterways, I'm looking to convert 60 gallons of fuel into liters. Could you assist me with that conversion? I tend to work more comfortably with liters.
- State view: `tree`
- Gold hop: h1: `gallon_to_liter(gallon=60.0)`
- 매칭 개수: 정확=1, 미매칭=1; 미매칭 gold=[]
- 검토 플래그: LLM judge override/rescue/downgrade 포함

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. gallon_to_liter(gallon=60.0)` | True/True | 정확 | h1: `gallon_to_liter({"gallon": 60.0})` (145) | h1: `gallon_to_liter({"gallon": 60.0})` (145) | schema_valid; exact_tool_name;parameter_overlap:gallon;argument_overlap:60.0,gallon,gallon_to_liter;schema_valid; hybrid_judge_override; judge=exact@0.98; judge_reason=The gener... |
| `2. liter_to_gallon(liter=($1).liter)` | True/True | 미매칭 | - | h1: `gallon_to_liter({"gallon": 60.0})` (5) | schema_valid; schema_valid;unresolved_input; no_candidate_above_threshold |

## multi_turn_base_87 turn 1
- 목표: Thank goodness! With the conversion sorted, I'd appreciate your help in ensuring that my vehicle's tank is topped up with 20 gallons of gasoline.
- State view: `tree`
- Gold hop: h2: `fillFuelTank(fuelAmount=20.0)`
- 매칭 개수: 미매칭=1; 미매칭 gold=['h2']
- 검토 플래그: 미매칭 gold hop: h2

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. liter_to_gallon(liter=20.0)` | True/True | 미매칭 | - | h2: `fillFuelTank({"fuelAmount": 20.0})` (15) | schema_valid; argument_overlap:20.0;schema_valid; no_candidate_above_threshold |

## multi_turn_base_87 turn 2
- 목표: Now, with the tank filled to my liking, I need to make sure my ride is prepared for this adventure. Could you help me start the engine, lock the doors, and engage the parking brake for a safe start?
- State view: `tree`
- Gold hop: h3: `activateParkingBrake(mode='engage')`; h4: `lockDoors(unlock=False, door=['driver', 'passenger', 'rear_left', 'rear_right'])`; h5: `pressBrakePedal(pedalPosition=1.0)`; h6: `startEngine(ignitionMode='START')`
- 매칭 개수: 정확=1, 미매칭=2; 미매칭 gold=['h3', 'h4', 'h5']
- 검토 플래그: 높은 점수 후보이나 primary 미매칭: u2->h4(175); LLM judge override/rescue/downgrade 포함; 미매칭 gold hop: h3,h4,h5

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. startEngine(ignitionMode="START")` | True/True | 정확 | h6: `startEngine({"ignitionMode": "START"})` (135) | h6: `startEngine({"ignitionMode": "START"})` (135) | schema_valid; exact_tool_name;parameter_overlap:ignitionMode;argument_overlap:ignitionmode,start;schema_valid |
| `2. lockDoors(unlock=True, door=["driver", "passenger", "rear_left", "rear_right"])` | True/True | 미매칭 | - | h4: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rear_right"]})` (175) | schema_valid; exact_tool_name;parameter_overlap:door,unlock;argument_overlap:door,driver,passenger,rear_left,rear_right,unlock;schema_valid; hybrid_judge_downgrade; judge=wrong@... |
| `3. releaseBrakePedal()` | True/True | 미매칭 | - | h3: `activateParkingBrake({"mode": "engage"})` (5) | schema_valid; no_candidate_above_threshold |

## multi_turn_base_87 turn 3
- 목표: Before setting off on this little expedition, can you do a quick tire pressure check for me? If any of the pressures fall below 33, kindly point me towards the nearest tire shop to get everything in tip-top shape before we roll.
- State view: `tree`
- Gold hop: h7: `check_tire_pressure()`; h8: `find_nearest_tire_shop()`
- 매칭 개수: 부분=1; 미매칭 gold=['h8']
- 검토 플래그: 미매칭 gold hop: h8

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. check_tire_pressure()` | True/True | 부분 | h7: `check_tire_pressure({})` (105) | h7: `check_tire_pressure({})` (105) | schema_valid; exact_tool_name;schema_valid |

## multi_turn_base_88 turn 0
- 목표: Hey, I've just filled my car up with 13.2 gallons of fuel. How much is that in liters?
- State view: `tree`
- Gold hop: h1: `gallon_to_liter(gallon=13.2)`
- 매칭 개수: 정확=1, 미매칭=1; 미매칭 gold=[]
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u2; LLM judge override/rescue/downgrade 포함

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. gallon_to_liter(gallon=13.2)` | True/True | 정확 | h1: `gallon_to_liter({"gallon": 13.2})` (135) | h1: `gallon_to_liter({"gallon": 13.2})` (135) | schema_valid; exact_tool_name;parameter_overlap:gallon;argument_overlap:13.2,gallon;schema_valid; hybrid_judge_override; judge=exact@0.99; judge_reason=The action exactly matche... |
| `2. liter_to_gallon(param=$1.liter)` | True/False | 미매칭 | - | h1: `gallon_to_liter({"gallon": 13.2})` (0) | missing_required: liter; unknown_parameters: param; schema_invalid;unresolved_input; no_candidate_above_threshold |

## multi_turn_base_88 turn 1
- 목표: Once you've converted it to liters, please guide me in filling the tank to the max limit. After that's sorted, I need to ensure that all the doors are securely locked and the parking brake is firmly set.
- State view: `tree`
- Gold hop: h2: `fillFuelTank(fuelAmount=36.8)`; h3: `lockDoors(unlock=False, door=['driver', 'passenger', 'rear_left', 'rear_right'])`; h4: `activateParkingBrake(mode='engage')`
- 매칭 개수: 부분=1, 미매칭=1; 미매칭 gold=['h2', 'h4']
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u2; LLM judge override/rescue/downgrade 포함; 미매칭 gold hop: h2,h4

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. startEngine(ignitionMode="START")` | True/True | 미매칭 | - | h2: `fillFuelTank({"fuelAmount": 36.8})` (5) | schema_valid; no_candidate_above_threshold |
| `2. lockDoors(door=["driver", "passenger"])` | True/False | 부분 | h3: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rear_right"]})` (140) | h3: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rear_right"]})` (140) | missing_required: unlock; exact_tool_name;parameter_overlap:door;argument_overlap:door,driver,passenger;schema_invalid; hybrid_judge_confirm; judge=partial@0.95; judge_reason=Th... |

## multi_turn_base_88 turn 2
- 목표: With the car prepped, I need to gear up for a drive from San Francisco to Rivermist. I'll be checking the fuel level once the engine is on in 'START' mode. Then, help me post a tweet, 'Embarking on an exciting road trip from SF to Rivermist!' and please throw in hashtags #Road...
- State view: `tree`
- Gold hop: h5: `pressBrakePedal(pedalPosition=1.0)`; h6: `startEngine(ignitionMode='START')`; h7: `post_tweet(content='Embarking on an exciting road trip from SF to Rivermist!', tags=['#RoadTrip', '#Adventure', '#Exploring'])`
- 매칭 개수: 정확=1, 미매칭=2; 미매칭 gold=['h5', 'h7']
- 검토 플래그: 미매칭 gold hop: h5,h7

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. startEngine(ignitionMode='START')` | True/True | 정확 | h6: `startEngine({"ignitionMode": "START"})` (135) | h6: `startEngine({"ignitionMode": "START"})` (135) | schema_valid; exact_tool_name;parameter_overlap:ignitionMode;argument_overlap:ignitionmode,start;schema_valid |
| `2. setCruiseControl(speed=60, activate=True, distanceToNextVehicle=100.0)` | True/True | 미매칭 | - | h5: `pressBrakePedal({"pedalPosition": 1.0})` (5) | schema_valid; no_candidate_above_threshold |
| `3. setHeadlights(mode='on')` | True/True | 미매칭 | - | h5: `pressBrakePedal({"pedalPosition": 1.0})` (5) | schema_valid; no_candidate_above_threshold |

## multi_turn_base_91 turn 0
- 목표: Hi, I am Kelly. I'm sweating. What's the temp outside right now? Would you be able to update Michael on today's outdoor temperature with message 'It is hot outside.'? He should know whether to bundle up or dress down for the weather.
- State view: `tree`
- Gold hop: h1: `get_outside_temperature_from_google()`; h2: `send_message(receiver_id='USR006', message='It is hot outside.')`
- 매칭 개수: 정확=1, 미매칭=1; 미매칭 gold=['h2']
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u2; LLM judge override/rescue/downgrade 포함; 미매칭 gold hop: h2

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. get_outside_temperature_from_google()` | True/True | 정확 | h1: `get_outside_temperature_from_google({})` (115) | h1: `get_outside_temperature_from_google({})` (115) | schema_valid; exact_tool_name;argument_overlap:get_outside_temperature_from_google;schema_valid; hybrid_judge_override; judge=exact@0.99; judge_reason=The generated action exact... |
| `2. get_outside_temperature_from_weather_com(param=$1)` | True/False | 미매칭 | - | h1: `get_outside_temperature_from_google({})` (0) | unknown_parameters: param; schema_invalid;unresolved_input; no_candidate_above_threshold |

## multi_turn_base_91 turn 1
- 목표: Let's review all the messages I have send so far.
- State view: `tree`
- Gold hop: h3: `view_messages_sent()`
- 매칭 개수: 미매칭=2; 미매칭 gold=['h3']
- 검토 플래그: 미매칭 gold hop: h3

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. get_outside_temperature_from_google()` | True/True | 미매칭 | - | h3: `view_messages_sent({})` (5) | schema_valid; no_candidate_above_threshold |
| `2. send_message(receiver_id='USR006', message='It is hot outside.')` | True/True | 미매칭 | - | h3: `view_messages_sent({})` (5) | schema_valid; no_candidate_above_threshold |

## multi_turn_base_97 turn 0
- 목표: I've heard a friend of mine in Rivermist recently visited Stonebrook, and she mentioned the journey felt quite extensive. I'm curious, do you happen to have an idea about the actual distance between the two places?
- State view: `tree`
- Gold hop: h1: `get_zipcode_based_on_city(city='Rivermist')`; h2: `get_zipcode_based_on_city(city='Stonebrook')`; h3: `estimate_distance(cityA='83214', cityB='74532')`
- 매칭 개수: (없음); 미매칭 gold=['h1', 'h2', 'h3']
- 검토 플래그: 미매칭 gold hop: h1,h2,h3; 생성된 parsed unit 없음

Parsed generated unit이 없다.

## multi_turn_base_97 turn 1
- 목표: Covering the distance from Rivermist to Stonebrook sure seems like a long trip. I'm a bit worried if my vehicle can endure the journey with the current fuel level. I'm not entirely sure how far my car can travel on the remaining fuel. What do you think?
- State view: `tree`
- Gold hop: h4: `estimate_drive_feasibility_by_mileage(distance=750.0)`
- 매칭 개수: 미매칭=3; 미매칭 gold=['h4']
- 검토 플래그: 미매칭 gold hop: h4

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. set_navigation(destination='Stonebrook')` | True/True | 미매칭 | - | h4: `estimate_drive_feasibility_by_mileage({"distance": 750.0})` (15) | schema_valid; argument_overlap:distance;schema_valid; no_candidate_above_threshold |
| `2. setHeadlights(mode='on')` | True/True | 미매칭 | - | h4: `estimate_drive_feasibility_by_mileage({"distance": 750.0})` (5) | schema_valid; no_candidate_above_threshold |
| `3. startEngine(ignitionMode='START')` | True/True | 미매칭 | - | h4: `estimate_drive_feasibility_by_mileage({"distance": 750.0})` (5) | schema_valid; no_candidate_above_threshold |

## multi_turn_base_97 turn 2
- 목표: Thanks a lot! Before I embark on this journey, it makes sense to ensure I won't be left stranded due to an empty tank. Just add to the tank fully.
- State view: `tree`
- Gold hop: h5: `fillFuelTank(fuelAmount=45.0)`
- 매칭 개수: 미매칭=2; 미매칭 gold=['h5']
- 검토 플래그: 높은 점수 후보이나 primary 미매칭: u1->h5(125); LLM judge override/rescue/downgrade 포함; 미매칭 gold hop: h5

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. fillFuelTank(fuelAmount=10.0)` | True/True | 미매칭 | - | h5: `fillFuelTank({"fuelAmount": 45.0})` (125) | schema_valid; exact_tool_name;parameter_overlap:fuelAmount;argument_overlap:fuelamount;schema_valid; hybrid_judge_downgrade; judge=wrong@0.98; judge_reason=Correct tool but wron... |
| `2. setHeadlights(mode='on')` | True/True | 미매칭 | - | h5: `fillFuelTank({"fuelAmount": 45.0})` (5) | schema_valid; no_candidate_above_threshold |

## multi_turn_base_97 turn 3
- 목표: Great, with my tank now full, let's embark on this journey. Once I'm set to go, I'd appreciate it if you could start the car for me.
- State view: `tree`
- Gold hop: h6: `lockDoors(unlock=False, door=['driver', 'passenger', 'rear_left', 'rear_right'])`; h7: `pressBrakePedal(pedalPosition=1.0)`; h8: `startEngine(ignitionMode='START')`
- 매칭 개수: 부분=2; 미매칭 gold=['h6', 'h7']
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u1; schema 오류 또는 arg/param wrapper 문제: u2; LLM judge override/rescue/downgrade 포함; 미매칭 gold hop: h6,h7

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. startEngine(arg={"ignitionMode": "START"})` | True/False | 부분 | h8: `startEngine({"ignitionMode": "START"})` (120) | h8: `startEngine({"ignitionMode": "START"})` (120) | missing_required: ignitionMode; unknown_parameters: arg; exact_tool_name;argument_overlap:ignitionmode,start;schema_invalid; hybrid_judge_rescue; judge=partial@0.91; judge_reaso... |
| `2. startEngine(arg={"ignitionMode": "START"})` | True/False | 부분 | h8: `startEngine({"ignitionMode": "START"})` (120) | h8: `startEngine({"ignitionMode": "START"})` (120) | missing_required: ignitionMode; unknown_parameters: arg; exact_tool_name;argument_overlap:ignitionmode,start;schema_invalid; hybrid_judge_override; judge=partial@0.93; judge_rea... |

## multi_turn_base_97 turn 4
- 목표: By the way, as I travel, there are some updates I need to communicate to my friend Michael. Would you be able to send message 'I am on my way.'?
- State view: `tree`
- Gold hop: h9: `send_message(receiver_id='BD732D1888B94DAA', message='I am on my way.')`
- 매칭 개수: 부분=1, 미매칭=1; 미매칭 gold=[]
- 검토 플래그: 제공되지 않은 tool 사용: u1:generate_message; schema 오류 또는 arg/param wrapper 문제: u2; LLM judge override/rescue/downgrade 포함

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. generate_message(message="I am on my way")` | False/False | 미매칭 | - | h9: `send_message({"receiver_id": "BD732D1888B94DAA", "message": "I am on my way."})` (50) | missing_tool_schema; parameter_overlap:message;argument_overlap:am,message,my,send_message;schema_invalid; no_candidate_above_threshold |
| `2. send_message(to="Michael", message="I am on my way")` | True/False | 부분 | h9: `send_message({"receiver_id": "BD732D1888B94DAA", "message": "I am on my way."})` (140) | h9: `send_message({"receiver_id": "BD732D1888B94DAA", "message": "I am on my way."})` (140) | missing_required: receiver_id; unknown_parameters: to; exact_tool_name;parameter_overlap:message;argument_overlap:am,message,my;schema_invalid; hybrid_judge_override; judge=part... |

## multi_turn_base_97 turn 5
- 목표: Lastly, while I'm on the road, I want to make sure I have informed everyone that should be aware. Could you display what messages I've send thus far?
- State view: `tree`
- Gold hop: h10: `view_messages_sent()`
- 매칭 개수: 미매칭=1; 미매칭 gold=['h10']
- 검토 플래그: 제공되지 않은 tool 사용: u1:display_messages; 미매칭 gold hop: h10

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. display_messages(user_ids=['USR002', 'BD732D1888B94DAA'])` | False/False | 미매칭 | - | h10: `view_messages_sent({})` (0) | missing_tool_schema; schema_invalid; no_candidate_above_threshold |

## multi_turn_base_143 turn 0
- 목표: I have recently come across Zeta Corp and I'm intrigued by their operations. Kindly include their stock in my watchlist so that I can monitor it.
- State view: `tree`
- Gold hop: h1: `add_to_watchlist(stock='ZETA')`
- 매칭 개수: 의미=1; 미매칭 gold=[]
- 검토 플래그: 제공되지 않은 tool 사용: u1:add_stock_to_watchlist; LLM judge override/rescue/downgrade 포함

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `2. add_stock_to_watchlist(symbol="ZETA")` | False/False | 의미 | h1: `add_to_watchlist({"stock": "ZETA"})` (20) | h1: `add_to_watchlist({"stock": "ZETA"})` (20) | missing_tool_schema; argument_overlap:stock,zeta;schema_invalid; hybrid_judge_rescue; judge=semantic@0.95; judge_reason=Generated add_stock_to_watchlist(symbol="ZETA") semantica... |

## multi_turn_base_143 turn 1
- 목표: I've been following a few orders and aim to review the specifics of one with a substantial order value I remember initiating. Let's retrieve the details.
- State view: `tree`
- Gold hop: h2: `get_order_details(order_id=12446)`
- 매칭 개수: 미매칭=1; 미매칭 gold=['h2']
- 검토 플래그: 높은 점수 후보이나 primary 미매칭: u1->h2(135); LLM judge override/rescue/downgrade 포함; 미매칭 gold hop: h2

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. get_order_details(order_id=12345)` | True/True | 미매칭 | - | h2: `get_order_details({"order_id": 12446})` (135) | schema_valid; exact_tool_name;parameter_overlap:order_id;argument_overlap:get_order_details,order_id;schema_valid; hybrid_judge_downgrade; judge=wrong@0.98; judge_reason=Same to... |

## multi_turn_base_143 turn 2
- 목표: With the recent market movements, my strategies are up for reevaluation. Proceed by cancelling the specific order we've just reviewed, given the uncertainties surrounding its outcome.
- State view: `tree`
- Gold hop: h3: `cancel_order(order_id=12446)`
- 매칭 개수: 미매칭=1; 미매칭 gold=['h3']
- 검토 플래그: 미매칭 gold hop: h3

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. get_order_details(order_id=12446)` | True/True | 미매칭 | - | h3: `cancel_order({"order_id": 12446})` (35) | schema_valid; parameter_overlap:order_id;argument_overlap:12446,order_id;schema_valid; no_candidate_above_threshold |

## multi_turn_base_143 turn 3
- 목표: I require some confidence about my current financial positioning. Share a detailed overview of my account, including balances and any associated card numbers. Furthermore, logging in as USR001 to notify my financial advisor (user id 'USR003') promptly about this potential shif...
- State view: `tree`
- Gold hop: h4: `message_login(user_id='USR001')`; h5: `get_account_info()`; h6: `send_message(receiver_id='USR003',message='My strategy is shifting due to recent market movements and the cancellation of a specific order. Current balance in my account is $10000.')`
- 매칭 개수: 부분=1; 미매칭 gold=['h4', 'h6']
- 검토 플래그: 미매칭 gold hop: h4,h6

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. get_account_info()` | True/True | 부분 | h5: `get_account_info({})` (105) | h5: `get_account_info({})` (105) | schema_valid; exact_tool_name;schema_valid |

## multi_turn_base_151 turn 0
- 목표: A complex decision awaits me. I'm planning an upcoming trip with limited resources and reevaluating my options. Could you first provide an estimate for a business class flight from San Francisco International to Los Angeles next Friday, November 10th, 2024, for an essential bu...
- State view: `tree`
- Gold hop: h1: `get_flight_cost(travel_from='SFO', travel_to='LAX', travel_date='2024-11-10', travel_class='business')`; h2: `compute_exchange_rate(base_currency='USD', target_currency='EUR', value=400.0)`; h3: `book_flight(access_token='abc123xyz', card_id='144756014165', travel_date='2024-11-10', travel_from='SFO', travel_to='LAX', travel_class='business')`
- 매칭 개수: 부분=2; 미매칭 gold=['h2', 'h3']
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u1; schema 오류 또는 arg/param wrapper 문제: u2; LLM judge override/rescue/downgrade 포함; 미매칭 gold hop: h2,h3

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. get_flight_cost(access_token="abc123xyz", travel_from="SFO", travel_to="LAX", travel_date="2024-11-10", travel_cla...` | True/False | 부분 | h1: `get_flight_cost({"travel_from": "SFO", "travel_to": "LAX", "travel_date": "2024-11-10",...` (180) | h1: `get_flight_cost({"travel_from": "SFO", "travel_to": "LAX", "travel_date": "2024-11-10",...` (180) | unknown_parameters: access_token, currency; exact_tool_name;parameter_overlap:travel_class,travel_date,travel_from,travel_to;argument_overlap:2024-11-10,business,lax,sfo,travel_... |
| `2. get_flight_cost(access_token="abc123xyz", travel_from="SFO", travel_to="LAX", travel_date="2024-11-10", travel_cla...` | True/False | 부분 | h1: `get_flight_cost({"travel_from": "SFO", "travel_to": "LAX", "travel_date": "2024-11-10",...` (180) | h1: `get_flight_cost({"travel_from": "SFO", "travel_to": "LAX", "travel_date": "2024-11-10",...` (180) | unknown_parameters: access_token, currency; exact_tool_name;parameter_overlap:travel_class,travel_date,travel_from,travel_to;argument_overlap:2024-11-10,business,lax,sfo,travel_... |

## multi_turn_base_151 turn 1
- 목표: Due to unforeseen circumstances, I'm unable to proceed with my journey to Los Angeles next week. Could the system initiate a cancellation process for the flight booking made earlier?
- State view: `tree`
- Gold hop: h4: `cancel_booking(access_token='abc123xyz', booking_id='3426812')`
- 매칭 개수: 정확=1; 미매칭 gold=[]

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. cancel_booking(access_token='abc123xyz', booking_id='3426812')` | True/True | 정확 | h4: `cancel_booking({"access_token": "abc123xyz", "booking_id": "3426812"})` (175) | h4: `cancel_booking({"access_token": "abc123xyz", "booking_id": "3426812"})` (175) | schema_valid; exact_tool_name;parameter_overlap:access_token,booking_id;argument_overlap:3426812,abc123xyz,access_token,booking_id,cancel_booking;schema_valid |

## multi_turn_base_151 turn 2
- 목표: I believe it would be strategic to communicate these adjustments to my extended network. Construct a tweet highlighting the cancellation of my travel plans, and ensure to add relevant hashtags 'TravelUpdate' and 'BusinessTrip' relating to travel and business updates, for messa...
- State view: `tree`
- Gold hop: h5: `authenticate_twitter(username='john',password='john1234')`; h6: `post_tweet(content='Just cancelled my trip to LA',tags=['#TravelUpdate','#BusinessTrip'])`
- 매칭 개수: 정확=1, 부분=1; 미매칭 gold=[]
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u2; LLM judge override/rescue/downgrade 포함

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. authenticate_twitter(username="john", password="john1234")` | True/True | 정확 | h5: `authenticate_twitter({"username": "john", "password": "john1234"})` (165) | h5: `authenticate_twitter({"username": "john", "password": "john1234"})` (165) | schema_valid; exact_tool_name;parameter_overlap:password,username;argument_overlap:john,john1234,password,username;schema_valid |
| `2. post_tweet(username="john", content="Just canceled my trip to LA. #TravelUpdate #BusinessTrip")` | True/False | 부분 | h6: `post_tweet({"content": "Just cancelled my trip to LA", "tags": ["#TravelUpdate", "#Busi...` (160) | h6: `post_tweet({"content": "Just cancelled my trip to LA", "tags": ["#TravelUpdate", "#Busi...` (160) | unknown_parameters: username; exact_tool_name;parameter_overlap:content;argument_overlap:businesstrip,content,just,my,travelupdate,trip;schema_invalid; hybrid_judge_override; ju... |

## multi_turn_base_173 turn 0
- 목표: I'm considering flying from Los Angeles Internationa (LAX) to John F. Kennedy (JFK) in business class on November 15, 2024. What would this flight typically cost?
- State view: `tree`
- Gold hop: h1: `get_flight_cost(travel_from='LAX', travel_to='JFK', travel_date='2024-11-15', travel_class='business')`
- 매칭 개수: (없음); 미매칭 gold=['h1']
- 검토 플래그: 미매칭 gold hop: h1; 생성된 parsed unit 없음

Parsed generated unit이 없다.

## multi_turn_base_173 turn 1
- 목표: Once I know the cost, I need that in pounds sterling — it's easier for my budget planning. Let's base future travel expenses on $10,000 using access token 'abc123xyz'.
- State view: `tree`
- Gold hop: h2: `compute_exchange_rate(base_currency='USD', target_currency='GBP', value=2400.0)`; h3: `set_budget_limit(access_token='abc123xyz', budget_limit=10000.0)`
- 매칭 개수: 미매칭=2; 미매칭 gold=['h2', 'h3']
- 검토 플래그: 제공되지 않은 tool 사용: u1:convert_currency; 제공되지 않은 tool 사용: u2:convert_currency; 미매칭 gold hop: h2,h3

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. convert_currency(access_token='abc123xyz', amount=2400.0, from_currency='USD', to_currency='USD')` | False/False | 미매칭 | - | h3: `set_budget_limit({"access_token": "abc123xyz", "budget_limit": 10000.0})` (30) | missing_tool_schema; parameter_overlap:access_token;argument_overlap:abc123xyz,access_token;schema_invalid; no_candidate_above_threshold |
| `2. convert_currency(access_token='abc123xyz', amount=10000.0, from_currency='USD', to_currency='USD')` | False/False | 미매칭 | - | h3: `set_budget_limit({"access_token": "abc123xyz", "budget_limit": 10000.0})` (40) | missing_tool_schema; parameter_overlap:access_token;argument_overlap:10000.0,abc123xyz,access_token;schema_invalid; no_candidate_above_threshold |

## multi_turn_base_173 turn 2
- 목표: Okay, I've sorted out my budget. Let's go ahead and book the flight as we discussed. Use my card — it's the one with id card_1496 —.
- State view: `tree`
- Gold hop: h4: `book_flight(access_token='abc123xyz', card_id='card_1496', travel_date='2024-11-15', travel_from='LAX', travel_to='JFK', travel_class='business')`
- 매칭 개수: 미매칭=2; 미매칭 gold=['h4']
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u2; 미매칭 gold hop: h4

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. compute_exchange_rate(base_currency='USD', target_currency='GBP', value=2400.0)` | True/True | 미매칭 | - | h4: `book_flight({"access_token": "abc123xyz", "card_id": "card_1496", "travel_date": "2024-...` (5) | schema_valid; no_candidate_above_threshold |
| `2. register_credit_card(access_token='abc123xyz', expiry_date='12/25', cardholder_name='Michael Thompson', card_numbe...` | True/False | 미매칭 | - | h4: `book_flight({"access_token": "abc123xyz", "card_id": "card_1496", "travel_date": "2024-...` (60) | missing_required: card_verification_number, expiration_date; unknown_parameters: card_id, expiry_date; parameter_overlap:access_token,card_id;argument_overlap:abc123xyz,access_t... |

## multi_turn_base_173 turn 3
- 목표: I noticed there's a ticket linked with this booking that I no longer find necessary. Can you cancel it on my behalf?
- State view: `tree`
- Gold hop: h5: `close_ticket(ticket_id='ticket_001')`
- 매칭 개수: 의미=1, 미매칭=1; 미매칭 gold=[]
- 검토 플래그: 제공되지 않은 tool 사용: u1:get_ticket_id; 제공되지 않은 tool 사용: u2:cancel_ticket; LLM judge override/rescue/downgrade 포함

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. get_ticket_id(access_token='abc123xyz', booking_id='booking_001')` | False/False | 미매칭 | - | h5: `close_ticket({"ticket_id": "ticket_001"})` (0) | missing_tool_schema; schema_invalid; no_candidate_above_threshold |
| `2. cancel_ticket(access_token='abc123xyz', ticket_id='ticket_001', reason='Unnecessary ticket')` | False/False | 의미 | h5: `close_ticket({"ticket_id": "ticket_001"})` (30) | h5: `close_ticket({"ticket_id": "ticket_001"})` (30) | missing_tool_schema; parameter_overlap:ticket_id;argument_overlap:ticket_001,ticket_id;schema_invalid; hybrid_judge_rescue; judge=semantic@0.88; judge_reason=The generated actio... |

## multi_turn_base_185 turn 0
- 목표: As I'm mapping out the logistics for my forthcoming business journey, I require an estimate for airfare traveling from the first to the second airport in your inventory, all set for December 15th, 2024. My travel funds should not exceed $2000, and I'll use my designated access...
- State view: `tree`
- Gold hop: h1: `list_all_airports()`; h2: `get_flight_cost(travel_from='RMS', travel_to='SBK', travel_date='2024-12-15', travel_class='business')`; h3: `set_budget_limit(access_token='12345-67890', budget_limit=2000.0)`
- 매칭 개수: 부분=1, 미매칭=1; 미매칭 gold=['h1', 'h2']
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u1; schema 오류 또는 arg/param wrapper 문제: u2; 높은 점수 후보이나 primary 미매칭: u1->h2(140); LLM judge override/rescue/downgrade 포함; 미매칭 gold hop: h1,h2

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. get_flight_cost(param=access_token=12345-67890,travel_from=SFO,travel_to=LAX,travel_date=2024-12-15)` | True/False | 미매칭 | - | h2: `get_flight_cost({"travel_from": "RMS", "travel_to": "SBK", "travel_date": "2024-12-15",...` (140) | syntax_error: invalid syntax; missing_required: travel_class, travel_date, travel_from, travel_to; exact_tool_name;argument_overlap:2024-12-15,travel_date,travel_from,travel_to;... |
| `2. set_budget_limit(param=access_token=12345-67890,budget_limit=2000.0)` | True/False | 부분 | h3: `set_budget_limit({"access_token": "12345-67890", "budget_limit": 2000.0})` (140) | h3: `set_budget_limit({"access_token": "12345-67890", "budget_limit": 2000.0})` (140) | syntax_error: invalid syntax; missing_required: access_token, budget_limit; exact_tool_name;argument_overlap:12345-67890,2000.0,access_token,budget_limit;schema_invalid; hybrid_... |

## multi_turn_base_185 turn 1
- 목표: Relating to the travel itinerary I'm arranging, I would like to secure travel insurance with a fee of $300 linked to booking code d184e2c0-2ebb-4f39-a525-d5e01b67dc6c. I'd prefer to utilize the payment method associated with card ID '0001'. Kindly finalize this with my access ...
- State view: `tree`
- Gold hop: h4: `purchase_insurance(access_token='12345-67890', insurance_type='comprehensive', booking_id='d184e2c0-2ebb-4f39-a525-d5e01b67dc6c', insurance_cost=300.0, card_id='0001')`
- 매칭 개수: 부분=1; 미매칭 gold=[]
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u1; LLM judge override/rescue/downgrade 포함

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. purchase_insurance(access_token='12345-67890', booking_id='d184e2c0-2ebb-4f39-a525-d5e01b67dc6c', card_id='0001', ...` | True/False | 부분 | h4: `purchase_insurance({"access_token": "12345-67890", "insurance_type": "comprehensive", "...` (180) | h4: `purchase_insurance({"access_token": "12345-67890", "insurance_type": "comprehensive", "...` (180) | missing_required: insurance_type; exact_tool_name;parameter_overlap:access_token,booking_id,card_id,insurance_cost;argument_overlap:0001,12345-67890,300.0,access_token,booking_i... |

## multi_turn_base_185 turn 2
- 목표: Could you assist by procuring the invoice for my reservation? I need to review the specifics to confirm precision, tapping into my access code 12345-67890 for verification.
- State view: `tree`
- Gold hop: h5: `retrieve_invoice(access_token='12345-67890', booking_id='d184e2c0-2ebb-4f39-a525-d5e01b67dc6c')`
- 매칭 개수: 정확=1; 미매칭 gold=[]

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. retrieve_invoice(access_token='12345-67890', booking_id=$1.booking_id)` | True/True | 정확 | h5: `retrieve_invoice({"access_token": "12345-67890", "booking_id": "d184e2c0-2ebb-4f39-a525...` (155) | h5: `retrieve_invoice({"access_token": "12345-67890", "booking_id": "d184e2c0-2ebb-4f39-a525...` (155) | schema_valid; exact_tool_name;parameter_overlap:access_token,booking_id;argument_overlap:12345-67890,access_token,booking_id;schema_valid;unresolved_input |
