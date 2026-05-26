# Matcher 검토 리포트: smoke_flat
각 turn마다 gold hop과 generated unit의 매칭 결과를 정리한 문서다. primary match가 없을 때도 가장 높은 점수의 후보를 같이 보여주어 matcher threshold와 scoring 품질을 검토할 수 있게 했다.
범례: 정확=같은 tool + schema-valid + argument overlap, 부분=threshold 이상이지만 약한 매칭, 미매칭=threshold를 넘은 후보 없음.
`valid/schema`는 각각 provided tool name 여부와 schema validation 통과 여부를 의미한다.

## multi_turn_base_35 turn 0
- 목표: Find a file named 'config.py' somewhere deep in the file system and once you have located it, display the last line of the first occuring file.
- Gold hop: h1: `cd(folder='projects')`; h2: `cd(folder='deep_folder')`; h3: `tail(file_name='config.py',lines=1)`
- 매칭 개수: (없음); 미매칭 gold=['h1', 'h2', 'h3']
- 검토 플래그: 미매칭 gold hop: h1,h2,h3; 생성된 parsed unit 없음

Parsed generated unit이 없다.

## multi_turn_base_35 turn 1
- 목표: This is actually not what I want. Could you display the entire content of the second file found.
- Gold hop: h4: `cat(file_name='real_config.py')`
- 매칭 개수: 미매칭=2; 미매칭 gold=['h4']
- 검토 플래그: 미매칭 gold hop: h4

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. cd(folder='projects')` | True/True | 미매칭 | - | h4: `cat({"file_name": "real_config.py"})` (15) | argument_overlap:cat;schema_valid |
| `2. cd(folder='deep_folder')` | True/True | 미매칭 | - | h4: `cat({"file_name": "real_config.py"})` (5) | schema_valid |

## multi_turn_base_35 turn 2
- 목표: Store the differences of the two file in a new file call diff.txt.
- Gold hop: h5: `diff(file_name1='config.py',file_name2='real_config.py')`; h6: `touch(file_name='diff.txt')`; h7: `echo(content='- Initialization of the system+ Real Config.',file_name='diff.txt')`
- 매칭 개수: 미매칭=3; 미매칭 gold=['h5', 'h6', 'h7']
- 검토 플래그: 높은 점수 후보이나 primary 미매칭: u3->h5(85); 미매칭 gold hop: h5,h6,h7

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. cd(folder='projects')` | True/True | 미매칭 | - | h5: `diff({"file_name1": "config.py", "file_name2": "real_config.py"})` (15) | argument_overlap:diff;schema_valid |
| `2. cd(folder='deep_folder')` | True/True | 미매칭 | - | h5: `diff({"file_name1": "config.py", "file_name2": "real_config.py"})` (5) | schema_valid |
| `3. cat(file_name='diff.txt')` | True/True | 미매칭 | - | h5: `diff({"file_name1": "config.py", "file_name2": "real_config.py"})` (85) | function_mention;schema_valid |

## multi_turn_base_39 turn 0
- 목표: I need you to set up a fresh folder named 'WebDevProjects' wherever you're currently working.
- Gold hop: h1: `mkdir(dir_name='WebDevProjects')`
- 매칭 개수: 부분=1; 미매칭 gold=[]
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u1

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. mkdir(arg={"dir_name": "WebDevProjects"})` | True/False | 부분 | h1: `mkdir({"dir_name": "WebDevProjects"})` (130) | h1: `mkdir({"dir_name": "WebDevProjects"})` (130) | missing_required: dir_name; unknown_parameters: arg |

## multi_turn_base_39 turn 1
- 목표: Populate the 'WebDevProjects' folder with 3 files:, 'styles.css', 'index.html', and 'script.js' with content 'Hello World!','Hi World!', 'Halo World!' in each.
- Gold hop: h2: `cd(folder='WebDevProjects')`; h3: `touch(file_name='styles.css')`; h4: `echo(content='Hello World!', file_name='styles.css')`; h5: `touch(file_name='index.html')`; h6: `echo(content='Hi World!', file_name='index.html')`; h7: `touch(file_name='script.js')`; h8: `echo(content='Halo World!', file_name='script.js')`
- 매칭 개수: 정확=6; 미매칭 gold=['h2']
- 검토 플래그: 미매칭 gold hop: h2

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. touch(file_name='styles.css')` | True/True | 정확 | h3: `touch({"file_name": "styles.css"})` (135) | h3: `touch({"file_name": "styles.css"})` (135) | exact_tool_name;parameter_overlap:file_name;argument_overlap:file_name,styles.css;schem... |
| `2. touch(file_name='index.html')` | True/True | 정확 | h5: `touch({"file_name": "index.html"})` (135) | h5: `touch({"file_name": "index.html"})` (135) | exact_tool_name;parameter_overlap:file_name;argument_overlap:file_name,index.html;schem... |
| `3. touch(file_name='script.js')` | True/True | 정확 | h7: `touch({"file_name": "script.js"})` (135) | h7: `touch({"file_name": "script.js"})` (135) | exact_tool_name;parameter_overlap:file_name;argument_overlap:file_name,script.js;schema... |
| `4. echo(file_name='styles.css', content='Hello World!')` | True/True | 정확 | h4: `echo({"content": "Hello World!", "file_name": "styles.css"})` (175) | h4: `echo({"content": "Hello World!", "file_name": "styles.css"})` (175) | exact_tool_name;parameter_overlap:content,file_name;argument_overlap:content,file_name,... |
| `5. echo(file_name='index.html', content='Hi World!')` | True/True | 정확 | h6: `echo({"content": "Hi World!", "file_name": "index.html"})` (175) | h6: `echo({"content": "Hi World!", "file_name": "index.html"})` (175) | exact_tool_name;parameter_overlap:content,file_name;argument_overlap:content,file_name,... |
| `6. echo(file_name='script.js', content='Halo World!')` | True/True | 정확 | h8: `echo({"content": "Halo World!", "file_name": "script.js"})` (175) | h8: `echo({"content": "Halo World!", "file_name": "script.js"})` (175) | exact_tool_name;parameter_overlap:content,file_name;argument_overlap:content,file_name,... |

## multi_turn_base_39 turn 2
- 목표: What's the second file name by system order? Don't list out hidden files.
- Gold hop: h9: `ls()`
- 매칭 개수: 부분=1, 미매칭=2; 미매칭 gold=[]
- 검토 플래그: 높은 점수 후보이나 primary 미매칭: u2->h9(100); schema 오류 또는 arg/param wrapper 문제: u3

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. cd(folder='WebDevProjects')` | True/True | 미매칭 | - | h9: `ls({})` (15) | argument_overlap:ls;schema_valid |
| `2. ls(file_name='styles.css')` | True/False | 미매칭 | - | h9: `ls({})` (100) | unknown_parameters: file_name |
| `3. ls(file_name='index.html')` | True/False | 부분 | h9: `ls({})` (100) | h9: `ls({})` (100) | unknown_parameters: file_name |

## multi_turn_base_39 turn 3
- 목표: Can you display the content of the first file by system order?
- Gold hop: h10: `cat(file_name='styles.css')`
- 매칭 개수: 정확=1, 미매칭=1; 미매칭 gold=[]

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. cd(folder='WebDevProjects')` | True/True | 미매칭 | - | h10: `cat({"file_name": "styles.css"})` (25) | argument_overlap:cat,styles.css;schema_valid |
| `2. cat(file_name='styles.css')` | True/True | 정확 | h10: `cat({"file_name": "styles.css"})` (135) | h10: `cat({"file_name": "styles.css"})` (135) | exact_tool_name;parameter_overlap:file_name;argument_overlap:file_name,styles.css;schem... |

## multi_turn_base_50 turn 0
- 목표: Hey there, I noticed that all of my car doors seem to have locked themselves up, and with my schedule being pretty tight today, I'm in quite a pinch. I could really use your help to get those doors unlocked. It'd be fantastic if you could also switch on the headlights. It's getting a bit darker o...
- Gold hop: h1: `lockDoors(unlock=True, door=['driver', 'passenger', 'rear_left', 'rear_right'])`; h2: `setHeadlights(mode='on')`
- 매칭 개수: 부분=2; 미매칭 gold=[]
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u1; schema 오류 또는 arg/param wrapper 문제: u2

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. lockDoors(arg={"unlock": True, "door": ["driver", "passenger", "rear_left", "rear_right"]})` | True/False | 부분 | h1: `lockDoors({"unlock": true, "door": ["driver", "passenger", "rear_left", "rear...` (150) | h1: `lockDoors({"unlock": true, "door": ["driver", "passenger", "rear_left", "rear...` (150) | missing_required: door, unlock; unknown_parameters: arg |
| `2. setHeadlights(arg={"mode": "on"})` | True/False | 부분 | h2: `setHeadlights({"mode": "on"})` (110) | h2: `setHeadlights({"mode": "on"})` (110) | missing_required: mode; unknown_parameters: arg |

## multi_turn_base_55 turn 0
- 목표: If the fuel level is lower than 10, then go ahead and add double that amount. Let's assume I will also head out right after, so feel free to start the engine using the necessary mode.
- Gold hop: h1: `displayCarStatus('fuel')`; h2: `fillFuelTank(15.0)`; h3: `lockDoors(unlock=False, door=['driver', 'passenger', 'rear_left', 'rear_right'])`; h4: `pressBrakePedal(pedalPosition=1.0)`; h5: `startEngine(ignitionMode='START')`
- 매칭 개수: 부분=2, 미매칭=3; 미매칭 gold=['h1', 'h3', 'h4']
- 검토 플래그: 제공되지 않은 tool 사용: u1:checkFuelLevel; 높은 점수 후보이나 primary 미매칭: u2->h2(100); schema 오류 또는 arg/param wrapper 문제: u3; 높은 점수 후보이나 primary 미매칭: u4->h5(120); schema 오류 또는 arg/param wrapper 문제: u5; 미매칭 gold hop: h1,h3,h4

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. checkFuelLevel()` | False/False | 미매칭 | - | h1: `displayCarStatus({"_arg0": "fuel"})` (10) | missing_tool_schema |
| `3. fillFuelTank(arg={"fuelAmount": 10})` | True/False | 미매칭 | - | h2: `fillFuelTank({"_arg0": 15.0})` (100) | missing_required: fuelAmount; unknown_parameters: arg |
| `4. fillFuelTank(arg={"fuelAmount": 10})` | True/False | 부분 | h2: `fillFuelTank({"_arg0": 15.0})` (100) | h2: `fillFuelTank({"_arg0": 15.0})` (100) | missing_required: fuelAmount; unknown_parameters: arg |
| `5. startEngine(arg={"ignitionMode": "START"})` | True/False | 미매칭 | - | h5: `startEngine({"ignitionMode": "START"})` (120) | missing_required: ignitionMode; unknown_parameters: arg |
| `6. startEngine(arg={"ignitionMode": "START"})` | True/False | 부분 | h5: `startEngine({"ignitionMode": "START"})` (120) | h5: `startEngine({"ignitionMode": "START"})` (120) | missing_required: ignitionMode; unknown_parameters: arg |

## multi_turn_base_55 turn 1
- 목표: Since we are all set to go, could you quickly check the pressure of all the tires to ensure everything is safe for our journey?
- Gold hop: h6: `check_tire_pressure()`
- 매칭 개수: 미매칭=2; 미매칭 gold=['h6']
- 검토 플래그: 미매칭 gold hop: h6

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. pressBrakePedal(pedalPosition=1.0)` | True/True | 미매칭 | - | h6: `check_tire_pressure({})` (15) | argument_overlap:check_tire_pressure;schema_valid |
| `2. startEngine(ignitionMode='START')` | True/True | 미매칭 | - | h6: `check_tire_pressure({})` (5) | schema_valid |

## multi_turn_base_55 turn 2
- 목표: The pressure seemed lower than expected. Let's open a ticket for 'Tire Pressure Issue', and detail it 'Urgent tire pressure issue.'. Given the urgency, classify this as the top priority to issue, where a higher score has more priority.
- Gold hop: h7: `create_ticket(title='Tire Pressure Issue', description='Urgent tire pressure issue.', priority=5)`
- 매칭 개수: 미매칭=1; 미매칭 gold=['h7']
- 검토 플래그: 미매칭 gold hop: h7

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. check_tire_pressure()` | True/True | 미매칭 | - | h7: `create_ticket({"title": "Tire Pressure Issue", "description": "Urgent tire pr...` (55) | argument_overlap:description,issue,issue.,pressure,priority,tire,tire pressure issue,ur... |

## multi_turn_base_55 turn 3
- 목표: Apparently, I never got feedback on the tire pressure ticket I created. Can you fetch that ticket for me so I can review the current status?
- Gold hop: h8: `get_ticket(ticket_id=2)`
- 매칭 개수: 미매칭=1; 미매칭 gold=['h8']
- 검토 플래그: 제공되지 않은 tool 사용: u1:fetch_ticket; 미매칭 gold hop: h8

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. fetch_ticket(ticket_id=2)` | False/False | 미매칭 | - | h8: `get_ticket({"ticket_id": 2})` (20) | missing_tool_schema |

## multi_turn_base_55 turn 4
- 목표: Great! They just gave me a call back. Now that I've checked the details, let's resolve the tire pressure ticket with an update stating 'Issue resolved!'.
- Gold hop: h9: `resolve_ticket(ticket_id=2, resolution='Issue resolved!')`
- 매칭 개수: 미매칭=1; 미매칭 gold=['h9']
- 검토 플래그: 제공되지 않은 tool 사용: u1:update_ticket; 미매칭 gold hop: h9

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. update_ticket(ticket_id=2, status='Resolved', description='Issue resolved!')` | False/False | 미매칭 | - | h9: `resolve_ticket({"ticket_id": 2, "resolution": "Issue resolved!"})` (50) | missing_tool_schema |

## multi_turn_base_56 turn 0
- 목표: I'm setting off on a road trip and my departure point is sunny San Francisco. Could you determine the distance to Rivermist to help me plan my fuel stops on the way?
- Gold hop: h1: `get_zipcode_based_on_city('San Francisco')`; h2: `get_zipcode_based_on_city('Rivermist')`; h3: `estimate_distance(cityA='94016', cityB='83214')`
- 매칭 개수: 부분=2; 미매칭 gold=['h3']
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u1; schema 오류 또는 arg/param wrapper 문제: u2; 미매칭 gold hop: h3

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. get_zipcode_based_on_city(city=<zipcode for San Francisco>)` | True/False | 부분 | h1: `get_zipcode_based_on_city({"_arg0": "San Francisco"})` (130) | h1: `get_zipcode_based_on_city({"_arg0": "San Francisco"})` (130) | syntax_error: invalid syntax; missing_required: city |
| `2. get_zipcode_based_on_city(city=<zipcode for Rivermist>)` | True/False | 부분 | h2: `get_zipcode_based_on_city({"_arg0": "Rivermist"})` (100) | h1: `get_zipcode_based_on_city({"_arg0": "San Francisco"})` (100) | syntax_error: invalid syntax; missing_required: city |

## multi_turn_base_56 turn 1
- 목표: Before embarking on this journey, please top up my vehicle to end with 50 gallons of fuel.
- Gold hop: h4: `displayCarStatus('fuel')`; h5: `fillFuelTank(fuelAmount=40)`
- 매칭 개수: 정확=1; 미매칭 gold=['h4']
- 검토 플래그: 미매칭 gold hop: h4

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. fillFuelTank(fuelAmount=50.0)` | True/True | 정확 | h5: `fillFuelTank({"fuelAmount": 40})` (135) | h5: `fillFuelTank({"fuelAmount": 40})` (135) | exact_tool_name;parameter_overlap:fuelAmount;argument_overlap:fillfueltank,fuelamount;s... |

## multi_turn_base_56 turn 2
- 목표: Please start the engine to prepare for our travel. Ensure that the car is locked and everything is secure for a seamless start.
- Gold hop: h6: `lockDoors(unlock=False, door=['driver', 'passenger', 'rear_left', 'rear_right'])`; h7: `pressBrakePedal(pedalPosition=1.0)`; h8: `startEngine(ignitionMode='START')`
- 매칭 개수: 정확=2, 미매칭=1; 미매칭 gold=['h7']
- 검토 플래그: 미매칭 gold hop: h7

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. lockDoors(unlock=True, door={["driver", "passenger", "rear_left", "rear_right"]})` | True/True | 정확 | h6: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rea...` (175) | h6: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rea...` (175) | exact_tool_name;parameter_overlap:door,unlock;argument_overlap:door,driver,passenger,re... |
| `2. displayCarStatus('engine')` | True/False | 미매칭 | - | h6: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rea...` (0) | positional_args_not_schema_checked; missing_required: option |
| `3. startEngine(ignitionMode='START')` | True/True | 정확 | h8: `startEngine({"ignitionMode": "START"})` (135) | h8: `startEngine({"ignitionMode": "START"})` (135) | exact_tool_name;parameter_overlap:ignitionMode;argument_overlap:ignitionmode,start;sche... |

## multi_turn_base_57 turn 0
- 목표: I've been thinking of visiting Autumnville for a while now, but I'm not sure how far it is from here in Crescent Hollow. Can you help me figure this out so I can plan my trip accordingly?
- Gold hop: h1: `get_zipcode_based_on_city('Crescent Hollow')`; h2: `get_zipcode_based_on_city('Autumnville')`; h3: `estimate_distance(cityA='69238', cityB='51479')`
- 매칭 개수: (없음); 미매칭 gold=['h1', 'h2', 'h3']
- 검토 플래그: 미매칭 gold hop: h1,h2,h3; 생성된 parsed unit 없음

Parsed generated unit이 없다.

## multi_turn_base_57 turn 1
- 목표: Oh, and by the way, there's something else I need help with. I want to calculate the logarithm of the distance you've just told me about, considering a base 10 with a precision of 5 digits. Could you provide me with this value as well?
- Gold hop: h4: `logarithm(value=630.0, base=10, precision=5)`
- 매칭 개수: 미매칭=3; 미매칭 gold=['h4']
- 검토 플래그: 미매칭 gold hop: h4

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. get_zipcode_based_on_city('Crescent Hollow')` | True/False | 미매칭 | - | h4: `logarithm({"value": 630.0, "base": 10, "precision": 5})` (40) | positional_args_not_schema_checked; missing_required: city |
| `2. get_zipcode_based_on_city('Autumnville')` | True/False | 미매칭 | - | h4: `logarithm({"value": 630.0, "base": 10, "precision": 5})` (0) | positional_args_not_schema_checked; missing_required: city |
| `3. estimate_distance(<Crescent Hollow>, <distance for Autumnville>)` | True/False | 미매칭 | - | h4: `logarithm({"value": 630.0, "base": 10, "precision": 5})` (0) | syntax_error: invalid syntax; missing_required: cityA, cityB |

## multi_turn_base_59 turn 0
- 목표: I recently moved to San Francisco and I’m planning a trip to Rivermist. How far apart are these places? I'd like to gauge the distance before setting off on this adventure.
- Gold hop: h1: `get_zipcode_based_on_city('San Francisco')`; h2: `get_zipcode_based_on_city('Rivermist')`; h3: `estimate_distance(cityA='94016', cityB='83214')`
- 매칭 개수: (없음); 미매칭 gold=['h1', 'h2', 'h3']
- 검토 플래그: 미매칭 gold hop: h1,h2,h3; 생성된 parsed unit 없음

Parsed generated unit이 없다.

## multi_turn_base_59 turn 1
- 목표: Now that I have the distance sorted, I'm considering the fuel situation. What's the current level of gasoline I have in liters?
- Gold hop: h4: `displayCarStatus(option='fuel')`; h5: `gallon_to_liter(gallon=10)`
- 매칭 개수: 미매칭=4; 미매칭 gold=['h4', 'h5']
- 검토 플래그: 제공되지 않은 tool 사용: u1:get_fuel_level; 제공되지 않은 tool 사용: u2:get_fuel_level; 제공되지 않은 tool 사용: u3:subtract_fuel_level; 제공되지 않은 tool 사용: u4:get_fuel_level; 미매칭 gold hop: h4,h5

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. get_fuel_level(city='San Francisco')` | False/False | 미매칭 | - | h4: `displayCarStatus({"option": "fuel"})` (10) | missing_tool_schema |
| `2. get_fuel_level(city='Rivermist')` | False/False | 미매칭 | - | h4: `displayCarStatus({"option": "fuel"})` (0) | missing_tool_schema |
| `3. subtract_fuel_level(cityA='San Francisco', cityB='Rivermist')` | False/False | 미매칭 | - | h4: `displayCarStatus({"option": "fuel"})` (0) | missing_tool_schema |
| `4. get_fuel_level(city='San Francisco')` | False/False | 미매칭 | - | h4: `displayCarStatus({"option": "fuel"})` (0) | missing_tool_schema |

## multi_turn_base_59 turn 2
- 목표: With the liters in mind, I'll need to top up my vehicle’s tank. Please go ahead and fill up the tank before I hit the road.
- Gold hop: h6: `fillFuelTank(fuelAmount=40)`
- 매칭 개수: 미매칭=3; 미매칭 gold=['h6']
- 검토 플래그: 제공되지 않은 tool 사용: u3:fill_up_fuel_tank; 미매칭 gold hop: h6

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. displayCarStatus(option='fuel')` | True/True | 미매칭 | - | h6: `fillFuelTank({"fuelAmount": 40})` (5) | schema_valid |
| `2. gallon_to_liter(gallon=10)` | True/True | 미매칭 | - | h6: `fillFuelTank({"fuelAmount": 40})` (5) | schema_valid |
| `3. fill_up_fuel_tank(liters=37.8541, targetLevel=50)` | False/False | 미매칭 | - | h6: `fillFuelTank({"fuelAmount": 40})` (0) | missing_tool_schema |

## multi_turn_base_59 turn 3
- 목표: As the journey is about to begin, could you kindly engage the 'START' ignition mode to ready the vehicle? I want to ensure everything's in perfect working order before I drive off.
- Gold hop: h7: `lockDoors(unlock=False, door=['driver', 'passenger', 'rear_left', 'rear_right'])`; h8: `pressBrakePedal(pedalPosition=1.0)`; h9: `startEngine(ignitionMode='START')`
- 매칭 개수: 미매칭=2; 미매칭 gold=['h7', 'h8', 'h9']
- 검토 플래그: 제공되지 않은 tool 사용: u2:setIgnitionMode; 미매칭 gold hop: h7,h8,h9

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. fillFuelTank(fuelAmount=40)` | True/True | 미매칭 | - | h9: `startEngine({"ignitionMode": "START"})` (15) | argument_overlap:start;schema_valid |
| `2. setIgnitionMode(mode='start')` | False/False | 미매칭 | - | h9: `startEngine({"ignitionMode": "START"})` (10) | missing_tool_schema |

## multi_turn_base_59 turn 4
- 목표: Finally, I'm analyzing mileage statistics and need the logarithm of the distance to the base the previous fuel value, computed to a precision of 10. Use base of 20. This will help with assessing the fuel efficiency patterns.
- Gold hop: h10: `logarithm(value=980.0, base=20, precision=10)`
- 매칭 개수: 미매칭=4; 미매칭 gold=['h10']
- 검토 플래그: 미매칭 gold hop: h10

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. displayCarStatus(option='fuel')` | True/True | 미매칭 | - | h10: `logarithm({"value": 980.0, "base": 20, "precision": 10})` (5) | schema_valid |
| `2. gallon_to_liter(gallon=10)` | True/True | 미매칭 | - | h10: `logarithm({"value": 980.0, "base": 20, "precision": 10})` (15) | argument_overlap:10;schema_valid |
| `3. fillFuelTank(fuelAmount=40)` | True/True | 미매칭 | - | h10: `logarithm({"value": 980.0, "base": 20, "precision": 10})` (5) | schema_valid |
| `4. startEngine(ignitionMode='AUTO')` | True/True | 미매칭 | - | h10: `logarithm({"value": 980.0, "base": 20, "precision": 10})` (5) | schema_valid |

## multi_turn_base_62 turn 0
- 목표: I'm currently in Rivermist planning a trip to Stonebrook. Could you provide an estimate of the distance and forward this info to my cousin Bob via text, in the format 'The distance from Rivermist to Stonebrook is xxx km.', where xxx is replaced by the distance value, in one decimal place)?
- Gold hop: h1: `get_zipcode_based_on_city('Rivermist')`; h2: `get_zipcode_based_on_city('Stonebrook')`; h3: `estimate_distance(cityA='83214', cityB='74532')`; h4: `send_message(receiver_id='USR002', message='The distance from Rivermist to Stonebrook is 750.0 km.')`
- 매칭 개수: 정확=2, 부분=1, 미매칭=1; 미매칭 gold=['h3']
- 검토 플래그: 제공되지 않은 tool 사용: u3:calculate_distance; schema 오류 또는 arg/param wrapper 문제: u4; 미매칭 gold hop: h3

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. get_zipcode_based_on_city(city=Rivermist)` | True/True | 정확 | h1: `get_zipcode_based_on_city({"_arg0": "Rivermist"})` (115) | h1: `get_zipcode_based_on_city({"_arg0": "Rivermist"})` (115) | exact_tool_name;argument_overlap:rivermist;schema_valid |
| `2. get_zipcode_based_on_city(city=Stonebrook)` | True/True | 정확 | h2: `get_zipcode_based_on_city({"_arg0": "Stonebrook"})` (115) | h2: `get_zipcode_based_on_city({"_arg0": "Stonebrook"})` (115) | exact_tool_name;argument_overlap:stonebrook;schema_valid |
| `3. calculate_distance(city1=<zipcode for Rivermist>, city2=<zipcode for Stonebrook>)` | False/False | 미매칭 | - | h1: `get_zipcode_based_on_city({"_arg0": "Rivermist"})` (0) | missing_tool_schema |
| `4. send_message(receiver=Bob, message="The distance from Rivermist to Stonebrook is <distance> km.", d...` | True/False | 부분 | h4: `send_message({"receiver_id": "USR002", "message": "The distance from Rivermis...` (150) | h4: `send_message({"receiver_id": "USR002", "message": "The distance from Rivermis...` (150) | missing_required: receiver_id; unknown_parameters: distance, receiver |

## multi_turn_base_62 turn 1
- 목표: As I set off on my drive, I need you to verify that all the doors on my car are securely locked, please.
- Gold hop: h5: `lockDoors(unlock=False, door=['driver', 'passenger', 'rear_left', 'rear_right'])`
- 매칭 개수: 정확=1, 미매칭=1; 미매칭 gold=[]
- 검토 플래그: 높은 점수 후보이나 primary 미매칭: u1->h5(160)

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. lockDoors(door=["driver", "passenger", "rear_left", "rear_right"])` | True/False | 미매칭 | - | h5: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rea...` (160) | missing_required: unlock |
| `2. lockDoors(unlock=True, door=["driver", "passenger", "rear_left", "rear_right"])` | True/True | 정확 | h5: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rea...` (175) | h5: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rea...` (175) | exact_tool_name;parameter_overlap:door,unlock;argument_overlap:door,driver,passenger,re... |

## multi_turn_base_62 turn 2
- 목표: After confirming the security of the vehicle, could you initiate the engine so I can check the fuel level?
- Gold hop: h6: `pressBrakePedal(pedalPosition=1.0)`; h7: `startEngine(ignitionMode='START')`
- 매칭 개수: 정확=1; 미매칭 gold=['h6']
- 검토 플래그: 미매칭 gold hop: h6

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. startEngine(ignitionMode='START')` | True/True | 정확 | h7: `startEngine({"ignitionMode": "START"})` (145) | h7: `startEngine({"ignitionMode": "START"})` (145) | exact_tool_name;parameter_overlap:ignitionMode;argument_overlap:ignitionmode,start,star... |

## multi_turn_base_62 turn 3
- 목표: Also, at your earliest convenience, can you show me all the messages I have send so far?
- Gold hop: h8: `view_messages_sent()`
- 매칭 개수: 미매칭=1; 미매칭 gold=['h8']
- 검토 플래그: 미매칭 gold hop: h8

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. send_message(receiver_id='USR002', message='The distance from Rivermist to Stonebrook is 750.0 km.')` | True/True | 미매칭 | - | h8: `view_messages_sent({})` (5) | schema_valid |

## multi_turn_base_67 turn 0
- 목표: Will you estimate the distance between San Francisco and Silverpine for me?
- Gold hop: h1: `get_zipcode_based_on_city('San Francisco')`; h2: `get_zipcode_based_on_city('Silverpine')`; h3: `estimate_distance(cityA='94016', cityB='62947')`
- 매칭 개수: (없음); 미매칭 gold=['h1', 'h2', 'h3']
- 검토 플래그: 미매칭 gold hop: h1,h2,h3; 생성된 parsed unit 없음

Parsed generated unit이 없다.

## multi_turn_base_67 turn 1
- 목표: I need that info to check if my vehicle can cover the distance without refueling.
- Gold hop: h4: `estimate_drive_feasibility_by_mileage(distance=780.0)`
- 매칭 개수: 미매칭=3; 미매칭 gold=['h4']
- 검토 플래그: 제공되지 않은 tool 사용: u1:get_fuel_level; 제공되지 않은 tool 사용: u2:get_fuel_consumption; 제공되지 않은 tool 사용: u3:calculate_fuel_needed_for_distance; 미매칭 gold hop: h4

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. get_fuel_level()` | False/False | 미매칭 | - | h4: `estimate_drive_feasibility_by_mileage({"distance": 780.0})` (10) | missing_tool_schema |
| `2. get_fuel_consumption()` | False/False | 미매칭 | - | h4: `estimate_drive_feasibility_by_mileage({"distance": 780.0})` (0) | missing_tool_schema |
| `3. calculate_fuel_needed_for_distance(distance='780.0', fuelConsumption='10.0')` | False/False | 미매칭 | - | h4: `estimate_drive_feasibility_by_mileage({"distance": 780.0})` (30) | missing_tool_schema |

## multi_turn_base_67 turn 2
- 목표: In case it can't, just fill out the fuel tank completely.
- Gold hop: h5: `fillFuelTank(fuelAmount=39.5)`
- 매칭 개수: 정확=1, 미매칭=1; 미매칭 gold=[]
- 검토 플래그: 제공되지 않은 tool 사용: u1:get_fuel_level

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. get_fuel_level()` | False/False | 미매칭 | - | h5: `fillFuelTank({"fuelAmount": 39.5})` (0) | missing_tool_schema |
| `2. fillFuelTank(fuelAmount=10.0)` | True/True | 정확 | h5: `fillFuelTank({"fuelAmount": 39.5})` (125) | h5: `fillFuelTank({"fuelAmount": 39.5})` (125) | exact_tool_name;parameter_overlap:fuelAmount;argument_overlap:fuelamount;schema_valid |

## multi_turn_base_67 turn 3
- 목표: Turn on my vehicle's engine in 'START' mode.
- Gold hop: h6: `lockDoors(unlock=False, door=['driver', 'passenger', 'rear_left', 'rear_right'])`; h7: `pressBrakePedal(pedalPosition=1.0)`; h8: `startEngine(ignitionMode='START')`
- 매칭 개수: 정확=1; 미매칭 gold=['h6', 'h7']
- 검토 플래그: 미매칭 gold hop: h6,h7

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. startEngine(ignitionMode='START')` | True/True | 정확 | h8: `startEngine({"ignitionMode": "START"})` (145) | h8: `startEngine({"ignitionMode": "START"})` (145) | exact_tool_name;parameter_overlap:ignitionMode;argument_overlap:ignitionmode,start,star... |

## multi_turn_base_70 turn 0
- 목표: Ensure the fuel tank is replenished adequately by adding 38 liters of gasoline so that we're well-prepared for the lengthy voyage ahead. Only fill with interger amount for volumn; round when not integer. Once fueled, proceed to start the engine confidently with the ignition mode, and make certain...
- Gold hop: h1: `liter_to_gallon(liter=38)`; h2: `fillFuelTank(fuelAmount=10)`; h3: `activateParkingBrake(mode='engage')`; h4: `lockDoors(unlock=False, door=['driver', 'passenger', 'rear_left', 'rear_right'])`; h5: `pressBrakePedal(pedalPosition=1.0)`; h6: `startEngine(ignitionMode='START')`
- 매칭 개수: 부분=2; 미매칭 gold=['h1', 'h3', 'h4', 'h5']
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u1; schema 오류 또는 arg/param wrapper 문제: u2; 미매칭 gold hop: h1,h3,h4,h5

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. fillFuelTank(arg={"fuelAmount": 38})` | True/False | 부분 | h2: `fillFuelTank({"fuelAmount": 10})` (120) | h2: `fillFuelTank({"fuelAmount": 10})` (120) | missing_required: fuelAmount; unknown_parameters: arg |
| `2. startEngine(arg={"ignitionMode": "START"})` | True/False | 부분 | h6: `startEngine({"ignitionMode": "START"})` (120) | h6: `startEngine({"ignitionMode": "START"})` (120) | missing_required: ignitionMode; unknown_parameters: arg |

## multi_turn_base_70 turn 1
- 목표: As we gear up for our adventure, it’s wise to confirm that each tire is inflated to a stable 32 PSI. Should any of the tires fall short, chart a course to the nearest tire service center to have this rectified.
- Gold hop: h7: `check_tire_pressure()`; h8: `find_nearest_tire_shop()`; h9: `set_navigation(destination='456 Oakwood Avenue, Rivermist, 83214')`
- 매칭 개수: 정확=1, 미매칭=1; 미매칭 gold=['h7', 'h8']
- 검토 플래그: 제공되지 않은 tool 사용: u1:checkTirePressure; 미매칭 gold hop: h7,h8

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. checkTirePressure(driverTire=32.0, passengerTire=32.0, rearLeftTire=32.0, rearRightTire=32.0)` | False/False | 미매칭 | - | h7: `check_tire_pressure({})` (0) | missing_tool_schema |
| `2. set_navigation(destination="123 Main St, Anytown, USA, 12345")` | True/True | 정확 | h9: `set_navigation({"destination": "456 Oakwood Avenue, Rivermist, 83214"})` (125) | h9: `set_navigation({"destination": "456 Oakwood Avenue, Rivermist, 83214"})` (125) | exact_tool_name;parameter_overlap:destination;argument_overlap:destination;schema_valid |

## multi_turn_base_71 turn 0
- 목표: Using my vehicle's system, estimate the distance between Rivermist and Stonebrook.
- Gold hop: h1: `get_zipcode_based_on_city('Rivermist')`; h2: `get_zipcode_based_on_city('Stonebrook')`; h3: `estimate_distance(cityA='83214', cityB='74532')`
- 매칭 개수: 부분=3; 미매칭 gold=[]
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u1; schema 오류 또는 arg/param wrapper 문제: u2; schema 오류 또는 arg/param wrapper 문제: u3

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. get_zipcode_based_on_city({"city": "Rivermist"})` | True/False | 부분 | h2: `get_zipcode_based_on_city({"_arg0": "Stonebrook"})` (120) | h1: `get_zipcode_based_on_city({"_arg0": "Rivermist"})` (120) | positional_args_not_schema_checked; missing_required: city |
| `2. get_zipcode_based_on_city({"city": "Stonebrook"})` | True/False | 부분 | h1: `get_zipcode_based_on_city({"_arg0": "Rivermist"})` (100) | h2: `get_zipcode_based_on_city({"_arg0": "Stonebrook"})` (110) | positional_args_not_schema_checked; missing_required: city |
| `3. estimate_distance({"city1": "<zipcode for Rivermist>", "city2": "<zipcode for Stonebrook>")` | True/False | 부분 | h3: `estimate_distance({"cityA": "83214", "cityB": "74532"})` (100) | h3: `estimate_distance({"cityA": "83214", "cityB": "74532"})` (100) | syntax_error: closing parenthesis ')' does not match opening parenthesis '{'; missing_r... |

## multi_turn_base_71 turn 1
- 목표: Assess if my vehicle's current mileage will suffice for the distance calculated. You don't need to re-fill, I just want to know.
- Gold hop: h4: `estimate_drive_feasibility_by_mileage(distance=750.0)`
- 매칭 개수: 미매칭=3; 미매칭 gold=['h4']
- 검토 플래그: 미매칭 gold hop: h4

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. get_zipcode_based_on_city('Rivermist')` | True/False | 미매칭 | - | h4: `estimate_drive_feasibility_by_mileage({"distance": 750.0})` (10) | positional_args_not_schema_checked; missing_required: city |
| `2. get_zipcode_based_on_city('Stonebrook')` | True/False | 미매칭 | - | h4: `estimate_drive_feasibility_by_mileage({"distance": 750.0})` (0) | positional_args_not_schema_checked; missing_required: city |
| `3. estimate_distance(cityA='83214', cityB='74532')` | True/True | 미매칭 | - | h4: `estimate_drive_feasibility_by_mileage({"distance": 750.0})` (5) | schema_valid |

## multi_turn_base_71 turn 2
- 목표: Fill the fuel tank to completely full.
- Gold hop: h5: `fillFuelTank(fuelAmount=45.0)`
- 매칭 개수: 정확=1, 미매칭=1; 미매칭 gold=[]
- 검토 플래그: 제공되지 않은 tool 사용: u1:get_fuel_level

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. get_fuel_level()` | False/False | 미매칭 | - | h5: `fillFuelTank({"fuelAmount": 45.0})` (10) | missing_tool_schema |
| `2. fillFuelTank(fuelAmount=50.0)` | True/True | 정확 | h5: `fillFuelTank({"fuelAmount": 45.0})` (125) | h5: `fillFuelTank({"fuelAmount": 45.0})` (125) | exact_tool_name;parameter_overlap:fuelAmount;argument_overlap:fuelamount;schema_valid |

## multi_turn_base_71 turn 3
- 목표: With the vehicle secured, start the engine for our prepared journey.
- Gold hop: h6: `lockDoors(unlock=False, door=['driver', 'passenger', 'rear_left', 'rear_right'])`; h7: `pressBrakePedal(pedalPosition=1.0)`; h8: `startEngine(ignitionMode='START')`
- 매칭 개수: 정확=1; 미매칭 gold=['h6', 'h7']
- 검토 플래그: 미매칭 gold hop: h6,h7

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. startEngine(ignitionMode='START')` | True/True | 정확 | h8: `startEngine({"ignitionMode": "START"})` (145) | h8: `startEngine({"ignitionMode": "START"})` (145) | exact_tool_name;parameter_overlap:ignitionMode;argument_overlap:ignitionmode,start,star... |

## multi_turn_base_71 turn 4
- 목표: Set navigation directly to Crescent Hollow, Spring, TX for a smooth ride without detours.
- Gold hop: h9: `set_navigation(destination='Crescent Hollow, Spring, TX')`
- 매칭 개수: 정확=1, 미매칭=2; 미매칭 gold=[]

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. set_navigation(destination='Crescent Hollow, Spring, TX')` | True/True | 정확 | h9: `set_navigation({"destination": "Crescent Hollow, Spring, TX"})` (165) | h9: `set_navigation({"destination": "Crescent Hollow, Spring, TX"})` (165) | exact_tool_name;parameter_overlap:destination;argument_overlap:crescent,crescent hollow... |
| `2. setCruiseControl(speed=60.0, activate=True, distanceToNextVehicle=10.0)` | True/True | 미매칭 | - | h9: `set_navigation({"destination": "Crescent Hollow, Spring, TX"})` (5) | schema_valid |
| `3. setHeadlights(mode='on')` | True/True | 미매칭 | - | h9: `set_navigation({"destination": "Crescent Hollow, Spring, TX"})` (5) | schema_valid |

## multi_turn_base_86 turn 0
- 목표: Lock all doors and engage the parking brake, then start the vehicle's engine in preparation for a trip. Afterward, check if our tire pressure condition is safe to proceed.
- Gold hop: h1: `lockDoors(unlock=False, door=['driver', 'passenger', 'rear_left', 'rear_right'])`; h2: `activateParkingBrake(mode='engage')`; h3: `pressBrakePedal(pedalPosition=1.0)`; h4: `startEngine(ignitionMode='START')`; h5: `check_tire_pressure()`
- 매칭 개수: 정확=3, 미매칭=1; 미매칭 gold=['h2', 'h5']
- 검토 플래그: 제공되지 않은 tool 사용: u4:checkTirePressure; 미매칭 gold hop: h2,h5

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. lockDoors(door=["driver", "passenger", "rear_left", "rear_right"], unlock=True)` | True/True | 정확 | h1: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rea...` (175) | h1: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rea...` (175) | exact_tool_name;parameter_overlap:door,unlock;argument_overlap:door,driver,passenger,re... |
| `2. pressBrakePedal(pedalPosition=0.5)` | True/True | 정확 | h3: `pressBrakePedal({"pedalPosition": 1.0})` (125) | h3: `pressBrakePedal({"pedalPosition": 1.0})` (125) | exact_tool_name;parameter_overlap:pedalPosition;argument_overlap:pedalposition;schema_v... |
| `3. startEngine(ignitionMode="START")` | True/True | 정확 | h4: `startEngine({"ignitionMode": "START"})` (135) | h4: `startEngine({"ignitionMode": "START"})` (135) | exact_tool_name;parameter_overlap:ignitionMode;argument_overlap:ignitionmode,start;sche... |
| `4. checkTirePressure(driver="front_rear_left", passenger="front_left", rear="front_right")` | False/False | 미매칭 | - | h1: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rea...` (20) | missing_tool_schema |

## multi_turn_base_86 turn 1
- 목표: The tire pressure seems worrying, kindly find the nearest tire shop to address the issue and set our navigation to that location.
- Gold hop: h6: `find_nearest_tire_shop()`; h7: `set_navigation(destination='456 Oakwood Avenue, Rivermist, 83214')`
- 매칭 개수: 정확=2; 미매칭 gold=[]

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. find_nearest_tire_shop()` | True/True | 정확 | h6: `find_nearest_tire_shop({})` (115) | h6: `find_nearest_tire_shop({})` (115) | exact_tool_name;argument_overlap:find_nearest_tire_shop;schema_valid |
| `2. set_navigation(destination="street, city, state")` | True/True | 정확 | h7: `set_navigation({"destination": "456 Oakwood Avenue, Rivermist, 83214"})` (125) | h7: `set_navigation({"destination": "456 Oakwood Avenue, Rivermist, 83214"})` (125) | exact_tool_name;parameter_overlap:destination;argument_overlap:destination;schema_valid |

## multi_turn_base_86 turn 2
- 목표: I have the tire issue fixed. Thinking aloud, since it's been a successful start to this journey, I'd like to send a thank you tweet 'Thank you to our vehicle for a smooth start!' about our vehicle with a few hashtags '#Journey, #SmoothRide, #Grateful' added.
- Gold hop: h8: `post_tweet(content='Thank you to our vehicle for a smooth start!', tags=['#Journey', '#SmoothRide', '#Grateful'])`
- 매칭 개수: 정확=1, 미매칭=1; 미매칭 gold=[]
- 검토 플래그: 제공되지 않은 tool 사용: u1:create_tweet

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. create_tweet(content="Thank you to our vehicle for a smooth start! #Journey, #SmoothRide, #Grateful")` | False/False | 미매칭 | - | h8: `post_tweet({"content": "Thank you to our vehicle for a smooth start!", "tags"...` (60) | missing_tool_schema |
| `2. post_tweet(content="Thank you to our vehicle for a smooth start! #Journey, #SmoothRide, #Grateful")` | True/True | 정확 | h8: `post_tweet({"content": "Thank you to our vehicle for a smooth start!", "tags"...` (165) | h8: `post_tweet({"content": "Thank you to our vehicle for a smooth start!", "tags"...` (165) | exact_tool_name;parameter_overlap:content;argument_overlap:content,grateful,journey,our... |

## multi_turn_base_87 turn 0
- 목표: As I gear up for another delightful journey exploring the captivating waterways, I'm looking to convert 60 gallons of fuel into liters. Could you assist me with that conversion? I tend to work more comfortably with liters.
- Gold hop: h1: `gallon_to_liter(gallon=60.0)`
- 매칭 개수: 정확=1; 미매칭 gold=[]

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. gallon_to_liter(gallon=60)` | True/True | 정확 | h1: `gallon_to_liter({"gallon": 60.0})` (135) | h1: `gallon_to_liter({"gallon": 60.0})` (135) | exact_tool_name;parameter_overlap:gallon;argument_overlap:gallon,gallon_to_liter;schema... |

## multi_turn_base_87 turn 1
- 목표: Thank goodness! With the conversion sorted, I'd appreciate your help in ensuring that my vehicle's tank is topped up with 20 gallons of gasoline.
- Gold hop: h2: `fillFuelTank(fuelAmount=20.0)`
- 매칭 개수: 미매칭=1; 미매칭 gold=['h2']
- 검토 플래그: 미매칭 gold hop: h2

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. gallon_to_liter(gallon=20.0)` | True/True | 미매칭 | - | h2: `fillFuelTank({"fuelAmount": 20.0})` (15) | argument_overlap:20.0;schema_valid |

## multi_turn_base_87 turn 2
- 목표: Now, with the tank filled to my liking, I need to make sure my ride is prepared for this adventure. Could you help me start the engine, lock the doors, and engage the parking brake for a safe start?
- Gold hop: h3: `activateParkingBrake(mode='engage')`; h4: `lockDoors(unlock=False, door=['driver', 'passenger', 'rear_left', 'rear_right'])`; h5: `pressBrakePedal(pedalPosition=1.0)`; h6: `startEngine(ignitionMode='START')`
- 매칭 개수: 부분=2, 미매칭=1; 미매칭 gold=['h3', 'h5']
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u1; schema 오류 또는 arg/param wrapper 문제: u2; 미매칭 gold hop: h3,h5

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. lockDoors(arg={"unlock": True, "door": ["driver", "passenger", "rear_left", "rear_right"]})` | True/False | 부분 | h4: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rea...` (150) | h4: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rea...` (150) | missing_required: door, unlock; unknown_parameters: arg |
| `2. startEngine(arg={"ignitionMode": "START"})` | True/False | 부분 | h6: `startEngine({"ignitionMode": "START"})` (120) | h6: `startEngine({"ignitionMode": "START"})` (120) | missing_required: ignitionMode; unknown_parameters: arg |
| `3. setHeadlights(arg={"mode": "on"})` | True/False | 미매칭 | - | h3: `activateParkingBrake({"mode": "engage"})` (10) | missing_required: mode; unknown_parameters: arg |

## multi_turn_base_87 turn 3
- 목표: Before setting off on this little expedition, can you do a quick tire pressure check for me? If any of the pressures fall below 33, kindly point me towards the nearest tire shop to get everything in tip-top shape before we roll.
- Gold hop: h7: `check_tire_pressure()`; h8: `find_nearest_tire_shop()`
- 매칭 개수: 미매칭=1; 미매칭 gold=['h7', 'h8']
- 검토 플래그: 미매칭 gold hop: h7,h8

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. get_zipcode_based_on_city(city="Rivermist")` | True/True | 미매칭 | - | h7: `check_tire_pressure({})` (5) | schema_valid |

## multi_turn_base_88 turn 0
- 목표: Hey, I've just filled my car up with 13.2 gallons of fuel. How much is that in liters?
- Gold hop: h1: `gallon_to_liter(gallon=13.2)`
- 매칭 개수: 정확=1, 미매칭=5; 미매칭 gold=[]
- 검토 플래그: 높은 점수 후보이나 primary 미매칭: u3->h1(135); 높은 점수 후보이나 primary 미매칭: u5->h1(135)

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. gallon_to_liter(gallon=13.2)` | True/True | 정확 | h1: `gallon_to_liter({"gallon": 13.2})` (145) | h1: `gallon_to_liter({"gallon": 13.2})` (145) | exact_tool_name;parameter_overlap:gallon;argument_overlap:13.2,gallon,gallon_to_liter;s... |
| `2. liter_to_gallon(liter=13.2)` | True/True | 미매칭 | - | h1: `gallon_to_liter({"gallon": 13.2})` (15) | argument_overlap:13.2;schema_valid |
| `3. gallon_to_liter(gallon=13.2)` | True/True | 미매칭 | - | h1: `gallon_to_liter({"gallon": 13.2})` (135) | exact_tool_name;parameter_overlap:gallon;argument_overlap:13.2,gallon;schema_valid |
| `4. liter_to_gallon(liter=13.2)` | True/True | 미매칭 | - | h1: `gallon_to_liter({"gallon": 13.2})` (15) | argument_overlap:13.2;schema_valid |
| `5. gallon_to_liter(gallon=13.2)` | True/True | 미매칭 | - | h1: `gallon_to_liter({"gallon": 13.2})` (135) | exact_tool_name;parameter_overlap:gallon;argument_overlap:13.2,gallon;schema_valid |
| `6. liter_to_gallon(liter=13.2)` | True/True | 미매칭 | - | h1: `gallon_to_liter({"gallon": 13.2})` (15) | argument_overlap:13.2;schema_valid |

## multi_turn_base_88 turn 1
- 목표: Once you've converted it to liters, please guide me in filling the tank to the max limit. After that's sorted, I need to ensure that all the doors are securely locked and the parking brake is firmly set.
- Gold hop: h2: `fillFuelTank(fuelAmount=36.8)`; h3: `lockDoors(unlock=False, door=['driver', 'passenger', 'rear_left', 'rear_right'])`; h4: `activateParkingBrake(mode='engage')`
- 매칭 개수: 정확=2, 미매칭=1; 미매칭 gold=['h4']
- 검토 플래그: 미매칭 gold hop: h4

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. liter_to_gallon(liter=49.967411999999996)` | True/True | 미매칭 | - | h2: `fillFuelTank({"fuelAmount": 36.8})` (5) | schema_valid |
| `2. fillFuelTank(fuelAmount=50)` | True/True | 정확 | h2: `fillFuelTank({"fuelAmount": 36.8})` (125) | h2: `fillFuelTank({"fuelAmount": 36.8})` (125) | exact_tool_name;parameter_overlap:fuelAmount;argument_overlap:fuelamount;schema_valid |
| `3. lockDoors(unlock=True, door=["driver", "passenger", "rear_left", "rear_right"])` | True/True | 정확 | h3: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rea...` (175) | h3: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rea...` (175) | exact_tool_name;parameter_overlap:door,unlock;argument_overlap:door,driver,passenger,re... |

## multi_turn_base_88 turn 2
- 목표: With the car prepped, I need to gear up for a drive from San Francisco to Rivermist. I'll be checking the fuel level once the engine is on in 'START' mode. Then, help me post a tweet, 'Embarking on an exciting road trip from SF to Rivermist!' and please throw in hashtags #RoadTrip #Adventure #Exp...
- Gold hop: h5: `pressBrakePedal(pedalPosition=1.0)`; h6: `startEngine(ignitionMode='START')`; h7: `post_tweet(content='Embarking on an exciting road trip from SF to Rivermist!', tags=['#RoadTrip', '#Adventure', '#Exp...`
- 매칭 개수: 정확=1, 미매칭=2; 미매칭 gold=['h5', 'h7']
- 검토 플래그: 미매칭 gold hop: h5,h7

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. startEngine(ignitionMode='START')` | True/True | 정확 | h6: `startEngine({"ignitionMode": "START"})` (135) | h6: `startEngine({"ignitionMode": "START"})` (135) | exact_tool_name;parameter_overlap:ignitionMode;argument_overlap:ignitionmode,start;sche... |
| `1. setCruiseControl(speed=60.0, activate=True, distanceToNextVehicle=10.0)` | True/True | 미매칭 | - | h5: `pressBrakePedal({"pedalPosition": 1.0})` (5) | schema_valid |
| `2. setHeadlights(mode='on')` | True/True | 미매칭 | - | h5: `pressBrakePedal({"pedalPosition": 1.0})` (5) | schema_valid |

## multi_turn_base_91 turn 0
- 목표: Hi, I am Kelly. I'm sweating. What's the temp outside right now? Would you be able to update Michael on today's outdoor temperature with message 'It is hot outside.'? He should know whether to bundle up or dress down for the weather.
- Gold hop: h1: `get_outside_temperature_from_google()`; h2: `send_message(receiver_id='USR006', message='It is hot outside.')`
- 매칭 개수: 미매칭=1; 미매칭 gold=['h1', 'h2']
- 검토 플래그: 미매칭 gold hop: h1,h2

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. get_outside_temperature_from_weather_com(outsideTemperature=25, message="It is hot outside.")` | True/False | 미매칭 | - | h2: `send_message({"receiver_id": "USR006", "message": "It is hot outside."})` (60) | unknown_parameters: message, outsideTemperature |

## multi_turn_base_91 turn 1
- 목표: Let's review all the messages I have send so far.
- Gold hop: h3: `view_messages_sent()`
- 매칭 개수: 미매칭=1; 미매칭 gold=['h3']
- 검토 플래그: 제공되지 않은 tool 사용: u1:retrieve_messages; 미매칭 gold hop: h3

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. retrieve_messages()` | False/False | 미매칭 | - | h3: `view_messages_sent({})` (0) | missing_tool_schema |

## multi_turn_base_97 turn 0
- 목표: I've heard a friend of mine in Rivermist recently visited Stonebrook, and she mentioned the journey felt quite extensive. I'm curious, do you happen to have an idea about the actual distance between the two places?
- Gold hop: h1: `get_zipcode_based_on_city(city='Rivermist')`; h2: `get_zipcode_based_on_city(city='Stonebrook')`; h3: `estimate_distance(cityA='83214', cityB='74532')`
- 매칭 개수: 부분=2, 미매칭=1; 미매칭 gold=['h3']
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u1; schema 오류 또는 arg/param wrapper 문제: u2; 제공되지 않은 tool 사용: u3:calculate_distance; 미매칭 gold hop: h3

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. get_zipcode_based_on_city(arg={"city": "<zipcode for Rivermist>"})` | True/False | 부분 | h2: `get_zipcode_based_on_city({"city": "Stonebrook"})` (120) | h1: `get_zipcode_based_on_city({"city": "Rivermist"})` (120) | missing_required: city; unknown_parameters: arg |
| `2. get_zipcode_based_on_city(arg={"city": "<zipcode for Stonebrook>"})` | True/False | 부분 | h1: `get_zipcode_based_on_city({"city": "Rivermist"})` (110) | h1: `get_zipcode_based_on_city({"city": "Rivermist"})` (110) | missing_required: city; unknown_parameters: arg |
| `3. calculate_distance(arg={"city1": "<zipcode for Rivermist>", "city2": "<zipcode for Stonebrook>")` | False/False | 미매칭 | - | h1: `get_zipcode_based_on_city({"city": "Rivermist"})` (0) | missing_tool_schema |

## multi_turn_base_97 turn 1
- 목표: Covering the distance from Rivermist to Stonebrook sure seems like a long trip. I'm a bit worried if my vehicle can endure the journey with the current fuel level. I'm not entirely sure how far my car can travel on the remaining fuel. What do you think?
- Gold hop: h4: `estimate_drive_feasibility_by_mileage(distance=750.0)`
- 매칭 개수: 미매칭=2; 미매칭 gold=['h4']
- 검토 플래그: 미매칭 gold hop: h4

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. startEngine(ignitionMode='START')` | True/True | 미매칭 | - | h4: `estimate_drive_feasibility_by_mileage({"distance": 750.0})` (5) | schema_valid |
| `2. startEngine(ignitionMode='RESTART')` | True/True | 미매칭 | - | h4: `estimate_drive_feasibility_by_mileage({"distance": 750.0})` (5) | schema_valid |

## multi_turn_base_97 turn 2
- 목표: Thanks a lot! Before I embark on this journey, it makes sense to ensure I won't be left stranded due to an empty tank. Just add to the tank fully.
- Gold hop: h5: `fillFuelTank(fuelAmount=45.0)`
- 매칭 개수: 정확=1, 미매칭=1; 미매칭 gold=[]

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. fillFuelTank(fuelAmount=10.0)` | True/True | 정확 | h5: `fillFuelTank({"fuelAmount": 45.0})` (125) | h5: `fillFuelTank({"fuelAmount": 45.0})` (125) | exact_tool_name;parameter_overlap:fuelAmount;argument_overlap:fuelamount;schema_valid |
| `2. startEngine(arg={"ignitionMode": "START"})` | True/False | 미매칭 | - | h5: `fillFuelTank({"fuelAmount": 45.0})` (0) | missing_required: ignitionMode; unknown_parameters: arg |

## multi_turn_base_97 turn 3
- 목표: Great, with my tank now full, let's embark on this journey. Once I'm set to go, I'd appreciate it if you could start the car for me.
- Gold hop: h6: `lockDoors(unlock=False, door=['driver', 'passenger', 'rear_left', 'rear_right'])`; h7: `pressBrakePedal(pedalPosition=1.0)`; h8: `startEngine(ignitionMode='START')`
- 매칭 개수: 정확=1, 미매칭=1; 미매칭 gold=['h6', 'h7']
- 검토 플래그: 제공되지 않은 tool 사용: u1:getEngineStatus; 미매칭 gold hop: h6,h7

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. getEngineStatus()` | False/False | 미매칭 | - | h8: `startEngine({"ignitionMode": "START"})` (10) | missing_tool_schema |
| `2. startEngine(ignitionMode='START')` | True/True | 정확 | h8: `startEngine({"ignitionMode": "START"})` (135) | h8: `startEngine({"ignitionMode": "START"})` (135) | exact_tool_name;parameter_overlap:ignitionMode;argument_overlap:ignitionmode,start;sche... |

## multi_turn_base_97 turn 4
- 목표: By the way, as I travel, there are some updates I need to communicate to my friend Michael. Would you be able to send message 'I am on my way.'?
- Gold hop: h9: `send_message(receiver_id='BD732D1888B94DAA', message='I am on my way.')`
- 매칭 개수: 미매칭=2; 미매칭 gold=['h9']
- 검토 플래그: 미매칭 gold hop: h9

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. setHeadlights(mode='off')` | True/True | 미매칭 | - | h9: `send_message({"receiver_id": "BD732D1888B94DAA", "message": "I am on my way."})` (15) | argument_overlap:message;schema_valid |
| `2. setHeadlights(mode='on')` | True/True | 미매칭 | - | h9: `send_message({"receiver_id": "BD732D1888B94DAA", "message": "I am on my way."})` (5) | schema_valid |

## multi_turn_base_97 turn 5
- 목표: Lastly, while I'm on the road, I want to make sure I have informed everyone that should be aware. Could you display what messages I've send thus far?
- Gold hop: h10: `view_messages_sent()`
- 매칭 개수: 미매칭=1; 미매칭 gold=['h10']
- 검토 플래그: 미매칭 gold hop: h10

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. send_message(receiver_id='BD732D1888B94DAA', message='I am on my way.')` | True/True | 미매칭 | - | h10: `view_messages_sent({})` (5) | schema_valid |

## multi_turn_base_143 turn 0
- 목표: I have recently come across Zeta Corp and I'm intrigued by their operations. Kindly include their stock in my watchlist so that I can monitor it.
- Gold hop: h1: `add_to_watchlist(stock='ZETA')`
- 매칭 개수: (없음); 미매칭 gold=['h1']
- 검토 플래그: 미매칭 gold hop: h1; 생성된 parsed unit 없음

Parsed generated unit이 없다.

## multi_turn_base_143 turn 1
- 목표: I've been following a few orders and aim to review the specifics of one with a substantial order value I remember initiating. Let's retrieve the details.
- Gold hop: h2: `get_order_details(order_id=12446)`
- 매칭 개수: 부분=1; 미매칭 gold=[]
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u1

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. get_order_details(order_id=<specific_order_id>)` | True/False | 부분 | h2: `get_order_details({"order_id": 12446})` (130) | h2: `get_order_details({"order_id": 12446})` (130) | syntax_error: invalid syntax; missing_required: order_id |

## multi_turn_base_143 turn 2
- 목표: With the recent market movements, my strategies are up for reevaluation. Proceed by cancelling the specific order we've just reviewed, given the uncertainties surrounding its outcome.
- Gold hop: h3: `cancel_order(order_id=12446)`
- 매칭 개수: 정확=1; 미매칭 gold=[]

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. cancel_order(order_id=12446)` | True/True | 정확 | h3: `cancel_order({"order_id": 12446})` (145) | h3: `cancel_order({"order_id": 12446})` (145) | exact_tool_name;parameter_overlap:order_id;argument_overlap:12446,cancel_order,order_id... |

## multi_turn_base_143 turn 3
- 목표: I require some confidence about my current financial positioning. Share a detailed overview of my account, including balances and any associated card numbers. Furthermore, logging in as USR001 to notify my financial advisor (user id 'USR003') promptly about this potential shift in my investment s...
- Gold hop: h4: `message_login(user_id='USR001')`; h5: `get_account_info()`; h6: `send_message(receiver_id='USR003',message='My strategy is shifting due to recent market movements and the cancellatio...`
- 매칭 개수: 미매칭=2; 미매칭 gold=['h4', 'h5', 'h6']
- 검토 플래그: 제공되지 않은 tool 사용: u2:notify_advisor; 미매칭 gold hop: h4,h5,h6

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. trading_login(username="USR001", password="password123")` | True/True | 미매칭 | - | h6: `send_message({"receiver_id": "USR003", "message": "My strategy is shifting du...` (55) | argument_overlap:account,market,message,movements,recent;schema_valid |
| `2. notify_advisor(user_id="USR003", message="My strategy is shifting due to recent market movements an...` | False/False | 미매칭 | - | h6: `send_message({"receiver_id": "USR003", "message": "My strategy is shifting du...` (50) | missing_tool_schema |

## multi_turn_base_151 turn 0
- 목표: A complex decision awaits me. I'm planning an upcoming trip with limited resources and reevaluating my options. Could you first provide an estimate for a business class flight from San Francisco International to Los Angeles next Friday, November 10th, 2024, for an essential business engagement? O...
- Gold hop: h1: `get_flight_cost(travel_from='SFO', travel_to='LAX', travel_date='2024-11-10', travel_class='business')`; h2: `compute_exchange_rate(base_currency='USD', target_currency='EUR', value=400.0)`; h3: `book_flight(access_token='abc123xyz', card_id='144756014165', travel_date='2024-11-10', travel_from='SFO', travel_to=...`
- 매칭 개수: 정확=1, 부분=1, 미매칭=1; 미매칭 gold=['h2']
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u3; 미매칭 gold hop: h2

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. get_flight_cost(travel_from="San Francisco International", travel_to="Los Angeles", travel_class="b...` | True/True | 정확 | h1: `get_flight_cost({"travel_from": "SFO", "travel_to": "LAX", "travel_date": "20...` (185) | h1: `get_flight_cost({"travel_from": "SFO", "travel_to": "LAX", "travel_date": "20...` (185) | exact_tool_name;parameter_overlap:travel_class,travel_date,travel_from,travel_to;argume... |
| `2. set_budget_limit(access_token="abc123xyz", budget_limit=2000)` | True/True | 미매칭 | - | h3: `book_flight({"access_token": "abc123xyz", "card_id": "144756014165", "travel_...` (35) | parameter_overlap:access_token;argument_overlap:abc123xyz,access_token;schema_valid |
| `3. book_flight(card_id="144756014165", access_token="abc123xyz")` | True/False | 부분 | h3: `book_flight({"access_token": "abc123xyz", "card_id": "144756014165", "travel_...` (160) | h3: `book_flight({"access_token": "abc123xyz", "card_id": "144756014165", "travel_...` (160) | missing_required: travel_class, travel_date, travel_from, travel_to |

## multi_turn_base_151 turn 1
- 목표: Due to unforeseen circumstances, I'm unable to proceed with my journey to Los Angeles next week. Could the system initiate a cancellation process for the flight booking made earlier?
- Gold hop: h4: `cancel_booking(access_token='abc123xyz', booking_id='3426812')`
- 매칭 개수: 미매칭=1; 미매칭 gold=['h4']
- 검토 플래그: 미매칭 gold hop: h4

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. book_flight(access_token='abc123xyz', card_id='144756014165', travel_date='2024-11-10', travel_from...` | True/True | 미매칭 | - | h4: `cancel_booking({"access_token": "abc123xyz", "booking_id": "3426812"})` (35) | parameter_overlap:access_token;argument_overlap:abc123xyz,access_token;schema_valid |

## multi_turn_base_151 turn 2
- 목표: I believe it would be strategic to communicate these adjustments to my extended network. Construct a tweet highlighting the cancellation of my travel plans, and ensure to add relevant hashtags 'TravelUpdate' and 'BusinessTrip' relating to travel and business updates, for message, just tell that '...
- Gold hop: h5: `authenticate_twitter(username='john',password='john1234')`; h6: `post_tweet(content='Just cancelled my trip to LA',tags=['#TravelUpdate','#BusinessTrip'])`
- 매칭 개수: 미매칭=2; 미매칭 gold=['h5', 'h6']
- 검토 플래그: 제공되지 않은 tool 사용: u1:create_tweet; 제공되지 않은 tool 사용: u2:authenticate; 미매칭 gold hop: h5,h6

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. create_tweet(message="Due to unforeseen circumstances, I had to cancel my travel plans. #TravelUpda...` | False/False | 미매칭 | - | h6: `post_tweet({"content": "Just cancelled my trip to LA", "tags": ["#TravelUpdat...` (50) | missing_tool_schema |
| `2. authenticate(username='john', password='john1234')` | False/False | 미매칭 | - | h5: `authenticate_twitter({"username": "john", "password": "john1234"})` (60) | missing_tool_schema |

## multi_turn_base_173 turn 0
- 목표: I'm considering flying from Los Angeles Internationa (LAX) to John F. Kennedy (JFK) in business class on November 15, 2024. What would this flight typically cost?
- Gold hop: h1: `get_flight_cost(travel_from='LAX', travel_to='JFK', travel_date='2024-11-15', travel_class='business')`
- 매칭 개수: (없음); 미매칭 gold=['h1']
- 검토 플래그: 미매칭 gold hop: h1; 생성된 parsed unit 없음

Parsed generated unit이 없다.

## multi_turn_base_173 turn 1
- 목표: Once I know the cost, I need that in pounds sterling — it's easier for my budget planning. Let's base future travel expenses on $10,000 using access token 'abc123xyz'.
- Gold hop: h2: `compute_exchange_rate(base_currency='USD', target_currency='GBP', value=2400.0)`; h3: `set_budget_limit(access_token='abc123xyz', budget_limit=10000.0)`
- 매칭 개수: 부분=1, 미매칭=1; 미매칭 gold=['h2']
- 검토 플래그: 제공되지 않은 tool 사용: u1:convert_currency; schema 오류 또는 arg/param wrapper 문제: u2; 미매칭 gold hop: h2

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. convert_currency(amount=2400.0, from_currency='USD', to_currency='USD')` | False/False | 미매칭 | - | h2: `compute_exchange_rate({"base_currency": "USD", "target_currency": "GBP", "val...` (20) | missing_tool_schema |
| `2. set_budget_limit(access_token='abc123xyz', budget_limit=10000.0, budget_currency='USD')` | True/False | 부분 | h3: `set_budget_limit({"access_token": "abc123xyz", "budget_limit": 10000.0})` (160) | h3: `set_budget_limit({"access_token": "abc123xyz", "budget_limit": 10000.0})` (160) | unknown_parameters: budget_currency |

## multi_turn_base_173 turn 2
- 목표: Okay, I've sorted out my budget. Let's go ahead and book the flight as we discussed. Use my card — it's the one with id card_1496 —.
- Gold hop: h4: `book_flight(access_token='abc123xyz', card_id='card_1496', travel_date='2024-11-15', travel_from='LAX', travel_to='JF...`
- 매칭 개수: 정확=1; 미매칭 gold=[]

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. book_flight(access_token='abc123xyz', travel_from='LAX', travel_to='JFK', travel_date='2024-11-15',...` | True/True | 정확 | h4: `book_flight({"access_token": "abc123xyz", "card_id": "card_1496", "travel_dat...` (185) | h4: `book_flight({"access_token": "abc123xyz", "card_id": "card_1496", "travel_dat...` (185) | exact_tool_name;parameter_overlap:access_token,card_id,travel_class,travel_date,travel_... |

## multi_turn_base_173 turn 3
- 목표: I noticed there's a ticket linked with this booking that I no longer find necessary. Can you cancel it on my behalf?
- Gold hop: h5: `close_ticket(ticket_id='ticket_001')`
- 매칭 개수: 미매칭=1; 미매칭 gold=['h5']
- 검토 플래그: 미매칭 gold hop: h5

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. book_flight(access_token='abc123xyz', card_id='card_1496', travel_date='2024-11-15', travel_from='L...` | True/True | 미매칭 | - | h5: `close_ticket({"ticket_id": "ticket_001"})` (5) | schema_valid |

## multi_turn_base_185 turn 0
- 목표: As I'm mapping out the logistics for my forthcoming business journey, I require an estimate for airfare traveling from the first to the second airport in your inventory, all set for December 15th, 2024. My travel funds should not exceed $2000, and I'll use my designated access code, 12345-67890. ...
- Gold hop: h1: `list_all_airports()`; h2: `get_flight_cost(travel_from='RMS', travel_to='SBK', travel_date='2024-12-15', travel_class='business')`; h3: `set_budget_limit(access_token='12345-67890', budget_limit=2000.0)`
- 매칭 개수: 부분=2; 미매칭 gold=['h1']
- 검토 플래그: schema 오류 또는 arg/param wrapper 문제: u1; schema 오류 또는 arg/param wrapper 문제: u2; 미매칭 gold hop: h1

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. get_flight_cost(arg={"travel_from": "Rivermist", "travel_to": "Stonebrook", "travel_date": "2024-12...` | True/False | 부분 | h2: `get_flight_cost({"travel_from": "RMS", "travel_to": "SBK", "travel_date": "20...` (140) | h2: `get_flight_cost({"travel_from": "RMS", "travel_to": "SBK", "travel_date": "20...` (140) | missing_required: travel_class, travel_date, travel_from, travel_to; unknown_parameters... |
| `2. set_budget_limit(arg={"access_token": "12345-67890", "budget_limit": 2000})` | True/False | 부분 | h3: `set_budget_limit({"access_token": "12345-67890", "budget_limit": 2000.0})` (130) | h3: `set_budget_limit({"access_token": "12345-67890", "budget_limit": 2000.0})` (130) | missing_required: access_token, budget_limit; unknown_parameters: arg |

## multi_turn_base_185 turn 1
- 목표: Relating to the travel itinerary I'm arranging, I would like to secure travel insurance with a fee of $300 linked to booking code d184e2c0-2ebb-4f39-a525-d5e01b67dc6c. I'd prefer to utilize the payment method associated with card ID '0001'. Kindly finalize this with my access code 12345-67890.
- Gold hop: h4: `purchase_insurance(access_token='12345-67890', insurance_type='comprehensive', booking_id='d184e2c0-2ebb-4f39-a525-d5...`
- 매칭 개수: 정확=1; 미매칭 gold=[]

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. purchase_insurance(access_token='12345-67890', insurance_type='travel', booking_id='d184e2c0-2ebb-4...` | True/True | 정확 | h4: `purchase_insurance({"access_token": "12345-67890", "insurance_type": "compreh...` (185) | h4: `purchase_insurance({"access_token": "12345-67890", "insurance_type": "compreh...` (185) | exact_tool_name;parameter_overlap:access_token,booking_id,card_id,insurance_cost,insura... |

## multi_turn_base_185 turn 2
- 목표: Could you assist by procuring the invoice for my reservation? I need to review the specifics to confirm precision, tapping into my access code 12345-67890 for verification.
- Gold hop: h5: `retrieve_invoice(access_token='12345-67890', booking_id='d184e2c0-2ebb-4f39-a525-d5e01b67dc6c')`
- 매칭 개수: 정확=1; 미매칭 gold=[]

| generated unit | valid/schema | 매칭 | primary gold | best candidate | 메모 |
|---|---|---|---|---|---|
| `1. retrieve_invoice(access_token='12345-67890')` | True/True | 정확 | h5: `retrieve_invoice({"access_token": "12345-67890", "booking_id": "d184e2c0-2ebb...` (135) | h5: `retrieve_invoice({"access_token": "12345-67890", "booking_id": "d184e2c0-2ebb...` (135) | exact_tool_name;parameter_overlap:access_token;argument_overlap:12345-67890,access_toke... |
