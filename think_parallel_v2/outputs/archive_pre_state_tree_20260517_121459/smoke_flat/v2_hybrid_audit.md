# think_parallel_v2 hybrid matcher audit

## Summary

- selected_judge_cases: `57`
- judged_pairs: `57`
- judge_errors: `0`

## Selection counts

| category | selected | judged |
|---|---:|---:|
| `argument_value_conflict` | 15 | 15 |
| `dependency_endpoint_unmatched` | 1 | 1 |
| `high_score_unmatched` | 7 | 7 |
| `schema_invalid_partial` | 23 | 23 |
| `semantic_tool_synonym_or_decomposition` | 15 | 15 |

## Cases

| case | categories | generated | candidate | judge | hybrid primary |
|---|---|---|---|---|---|
| multi_turn_base_143 t3 u2 | dependency_endpoint_unmatched,semantic_tool_synonym_or_decomposition | `2. notify_advisor(user_id="USR003", message="My strategy is shifting due to recent mark...` | h6: `send_message({"receiver_id": "USR003", "message": "My strategy is shifting due to recen...` | semantic c=0.90 | h6 / semantic / hybrid_judge_rescue |
| multi_turn_base_151 t2 u1 | semantic_tool_synonym_or_decomposition | `1. create_tweet(message="Due to unforeseen circumstances, I had to cancel my travel pla...` | h6: `post_tweet({"content": "Just cancelled my trip to LA", "tags": ["#TravelUpdate", "#Busi...` | partial c=0.78 | h6 / partial / hybrid_judge_rescue |
| multi_turn_base_151 t2 u2 | semantic_tool_synonym_or_decomposition | `2. authenticate(username='john', password='john1234')` | h5: `authenticate_twitter({"username": "john", "password": "john1234"})` | semantic c=0.88 | h5 / semantic / hybrid_judge_rescue |
| multi_turn_base_173 t1 u1 | semantic_tool_synonym_or_decomposition | `1. convert_currency(amount=2400.0, from_currency='USD', to_currency='USD')` | h2: `compute_exchange_rate({"base_currency": "USD", "target_currency": "GBP", "value": 2400.0})` | wrong c=0.96 | None / wrong / hybrid_p0 |
| multi_turn_base_35 t2 u3 | high_score_unmatched | `3. cat(file_name='diff.txt')` | h5: `diff({"file_name1": "config.py", "file_name2": "real_config.py"})` | wrong c=0.99 | None / wrong / hybrid_p0 |
| multi_turn_base_39 t2 u2 | high_score_unmatched | `2. ls(file_name='styles.css')` | h9: `ls({})` | wrong c=0.88 | None / wrong / hybrid_p0 |
| multi_turn_base_55 t0 u1 | semantic_tool_synonym_or_decomposition | `1. checkFuelLevel()` | h1: `displayCarStatus({"_arg0": "fuel"})` | semantic c=0.91 | h1 / semantic / hybrid_judge_rescue |
| multi_turn_base_55 t0 u2 | high_score_unmatched | `3. fillFuelTank(arg={"fuelAmount": 10})` | h2: `fillFuelTank({"_arg0": 15.0})` | wrong c=0.95 | None / wrong / hybrid_p0 |
| multi_turn_base_55 t0 u3 | argument_value_conflict,schema_invalid_partial | `4. fillFuelTank(arg={"fuelAmount": 10})` | h2: `fillFuelTank({"_arg0": 15.0})` | wrong c=0.95 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_55 t0 u4 | high_score_unmatched | `5. startEngine(arg={"ignitionMode": "START"})` | h5: `startEngine({"ignitionMode": "START"})` | partial c=0.90 | h5 / partial / hybrid_judge_rescue |
| multi_turn_base_55 t3 u1 | semantic_tool_synonym_or_decomposition | `1. fetch_ticket(ticket_id=2)` | h8: `get_ticket({"ticket_id": 2})` | semantic c=0.95 | h8 / semantic / hybrid_judge_rescue |
| multi_turn_base_55 t4 u1 | semantic_tool_synonym_or_decomposition | `1. update_ticket(ticket_id=2, status='Resolved', description='Issue resolved!')` | h9: `resolve_ticket({"ticket_id": 2, "resolution": "Issue resolved!"})` | semantic c=0.86 | h9 / semantic / hybrid_judge_rescue |
| multi_turn_base_56 t1 u1 | argument_value_conflict | `1. fillFuelTank(fuelAmount=50.0)` | h5: `fillFuelTank({"fuelAmount": 40})` | wrong c=0.98 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_56 t2 u1 | argument_value_conflict | `1. lockDoors(unlock=True, door={["driver", "passenger", "rear_left", "rear_right"]})` | h6: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rear_right"]})` | wrong c=0.98 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_59 t1 u1 | semantic_tool_synonym_or_decomposition | `1. get_fuel_level(city='San Francisco')` | h4: `displayCarStatus({"option": "fuel"})` | partial c=0.78 | h4 / partial / hybrid_judge_rescue |
| multi_turn_base_59 t3 u2 | semantic_tool_synonym_or_decomposition | `2. setIgnitionMode(mode='start')` | h9: `startEngine({"ignitionMode": "START"})` | semantic c=0.92 | h9 / semantic / hybrid_judge_rescue |
| multi_turn_base_62 t1 u1 | high_score_unmatched | `1. lockDoors(door=["driver", "passenger", "rear_left", "rear_right"])` | h5: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rear_right"]})` | partial c=0.88 | h5 / partial / hybrid_judge_rescue |
| multi_turn_base_62 t1 u2 | argument_value_conflict | `2. lockDoors(unlock=True, door=["driver", "passenger", "rear_left", "rear_right"])` | h5: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rear_right"]})` | wrong c=0.99 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_67 t1 u1 | semantic_tool_synonym_or_decomposition | `1. get_fuel_level()` | h4: `estimate_drive_feasibility_by_mileage({"distance": 780.0})` | wrong c=0.90 | None / wrong / hybrid_p0 |
| multi_turn_base_67 t1 u3 | semantic_tool_synonym_or_decomposition | `3. calculate_fuel_needed_for_distance(distance='780.0', fuelConsumption='10.0')` | h4: `estimate_drive_feasibility_by_mileage({"distance": 780.0})` | partial c=0.87 | None / wrong / hybrid_p0 |
| multi_turn_base_67 t2 u2 | argument_value_conflict | `2. fillFuelTank(fuelAmount=10.0)` | h5: `fillFuelTank({"fuelAmount": 39.5})` | wrong c=0.97 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_70 t0 u1 | argument_value_conflict,schema_invalid_partial | `1. fillFuelTank(arg={"fuelAmount": 38})` | h2: `fillFuelTank({"fuelAmount": 10})` | wrong c=0.95 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_70 t1 u2 | argument_value_conflict | `2. set_navigation(destination="123 Main St, Anytown, USA, 12345")` | h9: `set_navigation({"destination": "456 Oakwood Avenue, Rivermist, 83214"})` | wrong c=0.98 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_71 t2 u1 | semantic_tool_synonym_or_decomposition | `1. get_fuel_level()` | h5: `fillFuelTank({"fuelAmount": 45.0})` | wrong c=0.98 | None / wrong / hybrid_p0 |
| multi_turn_base_71 t2 u2 | argument_value_conflict | `2. fillFuelTank(fuelAmount=50.0)` | h5: `fillFuelTank({"fuelAmount": 45.0})` | wrong c=0.98 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_86 t0 u1 | argument_value_conflict | `1. lockDoors(door=["driver", "passenger", "rear_left", "rear_right"], unlock=True)` | h1: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rear_right"]})` | wrong c=0.98 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_86 t0 u2 | argument_value_conflict | `2. pressBrakePedal(pedalPosition=0.5)` | h3: `pressBrakePedal({"pedalPosition": 1.0})` | wrong c=0.98 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_86 t0 u4 | semantic_tool_synonym_or_decomposition | `4. checkTirePressure(driver="front_rear_left", passenger="front_left", rear="front_right")` | h1: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rear_right"]})` | wrong c=0.98 | None / wrong / hybrid_p0 |
| multi_turn_base_86 t2 u1 | semantic_tool_synonym_or_decomposition | `1. create_tweet(content="Thank you to our vehicle for a smooth start! #Journey, #Smooth...` | h8: `post_tweet({"content": "Thank you to our vehicle for a smooth start!", "tags": ["#Journ...` | semantic c=0.86 | h8 / semantic / hybrid_judge_rescue |
| multi_turn_base_87 t0 u1 | argument_value_conflict | `1. gallon_to_liter(gallon=60)` | h1: `gallon_to_liter({"gallon": 60.0})` | exact c=1.00 | h1 / exact / hybrid_judge_override |
| multi_turn_base_87 t2 u1 | argument_value_conflict,schema_invalid_partial | `1. lockDoors(arg={"unlock": True, "door": ["driver", "passenger", "rear_left", "rear_ri...` | h4: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rear_right"]})` | wrong c=0.97 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_88 t0 u3 | high_score_unmatched | `3. gallon_to_liter(gallon=13.2)` | h1: `gallon_to_liter({"gallon": 13.2})` | exact c=1.00 | h1 / exact / hybrid_judge_rescue |
| multi_turn_base_88 t0 u5 | high_score_unmatched | `5. gallon_to_liter(gallon=13.2)` | h1: `gallon_to_liter({"gallon": 13.2})` | exact c=1.00 | h1 / exact / hybrid_judge_rescue |
| multi_turn_base_88 t1 u2 | argument_value_conflict | `2. fillFuelTank(fuelAmount=50)` | h2: `fillFuelTank({"fuelAmount": 36.8})` | wrong c=0.96 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_88 t1 u3 | argument_value_conflict | `3. lockDoors(unlock=True, door=["driver", "passenger", "rear_left", "rear_right"])` | h3: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rear_right"]})` | wrong c=0.99 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_97 t2 u1 | argument_value_conflict | `1. fillFuelTank(fuelAmount=10.0)` | h5: `fillFuelTank({"fuelAmount": 45.0})` | wrong c=0.98 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_97 t3 u1 | semantic_tool_synonym_or_decomposition | `1. getEngineStatus()` | h8: `startEngine({"ignitionMode": "START"})` | wrong c=0.98 | None / wrong / hybrid_p0 |
| multi_turn_base_143 t1 u1 | schema_invalid_partial | `1. get_order_details(order_id=<specific_order_id>)` | h2: `get_order_details({"order_id": 12446})` | partial c=0.78 | h2 / partial / hybrid_judge_override |
| multi_turn_base_151 t0 u3 | schema_invalid_partial | `3. book_flight(card_id="144756014165", access_token="abc123xyz")` | h3: `book_flight({"access_token": "abc123xyz", "card_id": "144756014165", "travel_date": "20...` | partial c=0.86 | h3 / partial / hybrid_judge_override |
| multi_turn_base_173 t1 u2 | schema_invalid_partial | `2. set_budget_limit(access_token='abc123xyz', budget_limit=10000.0, budget_currency='USD')` | h3: `set_budget_limit({"access_token": "abc123xyz", "budget_limit": 10000.0})` | partial c=0.88 | h3 / partial / hybrid_judge_override |
| multi_turn_base_185 t0 u1 | schema_invalid_partial | `1. get_flight_cost(arg={"travel_from": "Rivermist", "travel_to": "Stonebrook", "travel_...` | h2: `get_flight_cost({"travel_from": "RMS", "travel_to": "SBK", "travel_date": "2024-12-15",...` | partial c=0.86 | h2 / partial / hybrid_judge_override |
| multi_turn_base_185 t0 u2 | schema_invalid_partial | `2. set_budget_limit(arg={"access_token": "12345-67890", "budget_limit": 2000})` | h3: `set_budget_limit({"access_token": "12345-67890", "budget_limit": 2000.0})` | partial c=0.96 | h3 / partial / hybrid_judge_override |
| multi_turn_base_39 t0 u1 | schema_invalid_partial | `1. mkdir(arg={"dir_name": "WebDevProjects"})` | h1: `mkdir({"dir_name": "WebDevProjects"})` | partial c=0.94 | h1 / partial / hybrid_judge_override |
| multi_turn_base_39 t2 u3 | schema_invalid_partial | `3. ls(file_name='index.html')` | h9: `ls({})` | wrong c=0.88 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_50 t0 u1 | schema_invalid_partial | `1. lockDoors(arg={"unlock": True, "door": ["driver", "passenger", "rear_left", "rear_ri...` | h1: `lockDoors({"unlock": true, "door": ["driver", "passenger", "rear_left", "rear_right"]})` | partial c=0.93 | h1 / partial / hybrid_judge_override |
| multi_turn_base_50 t0 u2 | schema_invalid_partial | `2. setHeadlights(arg={"mode": "on"})` | h2: `setHeadlights({"mode": "on"})` | partial c=0.96 | h2 / partial / hybrid_judge_override |
| multi_turn_base_55 t0 u5 | schema_invalid_partial | `6. startEngine(arg={"ignitionMode": "START"})` | h5: `startEngine({"ignitionMode": "START"})` | partial c=0.92 | h5 / partial / hybrid_judge_override |
| multi_turn_base_56 t0 u1 | schema_invalid_partial | `1. get_zipcode_based_on_city(city=<zipcode for San Francisco>)` | h1: `get_zipcode_based_on_city({"_arg0": "San Francisco"})` | partial c=0.83 | h1 / partial / hybrid_judge_override |
| multi_turn_base_56 t0 u2 | schema_invalid_partial | `2. get_zipcode_based_on_city(city=<zipcode for Rivermist>)` | h2: `get_zipcode_based_on_city({"_arg0": "Rivermist"})` | partial c=0.82 | h2 / partial / hybrid_judge_override |
| multi_turn_base_62 t0 u4 | schema_invalid_partial | `4. send_message(receiver=Bob, message="The distance from Rivermist to Stonebrook is <di...` | h4: `send_message({"receiver_id": "USR002", "message": "The distance from Rivermist to Stone...` | partial c=0.86 | h4 / partial / hybrid_judge_override |
| multi_turn_base_70 t0 u2 | schema_invalid_partial | `2. startEngine(arg={"ignitionMode": "START"})` | h6: `startEngine({"ignitionMode": "START"})` | partial c=0.93 | h6 / partial / hybrid_judge_override |
| multi_turn_base_71 t0 u1 | schema_invalid_partial | `1. get_zipcode_based_on_city({"city": "Rivermist"})` | h2: `get_zipcode_based_on_city({"_arg0": "Stonebrook"})` | wrong c=0.98 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_71 t0 u2 | schema_invalid_partial | `2. get_zipcode_based_on_city({"city": "Stonebrook"})` | h1: `get_zipcode_based_on_city({"_arg0": "Rivermist"})` | wrong c=0.98 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_71 t0 u3 | schema_invalid_partial | `3. estimate_distance({"city1": "<zipcode for Rivermist>", "city2": "<zipcode for Stoneb...` | h3: `estimate_distance({"cityA": "83214", "cityB": "74532"})` | partial c=0.86 | h3 / partial / hybrid_judge_override |
| multi_turn_base_87 t2 u2 | schema_invalid_partial | `2. startEngine(arg={"ignitionMode": "START"})` | h6: `startEngine({"ignitionMode": "START"})` | partial c=0.90 | h6 / partial / hybrid_judge_override |
| multi_turn_base_97 t0 u1 | schema_invalid_partial | `1. get_zipcode_based_on_city(arg={"city": "<zipcode for Rivermist>"})` | h2: `get_zipcode_based_on_city({"city": "Stonebrook"})` | wrong c=0.97 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_97 t0 u2 | schema_invalid_partial | `2. get_zipcode_based_on_city(arg={"city": "<zipcode for Stonebrook>"})` | h1: `get_zipcode_based_on_city({"city": "Rivermist"})` | wrong c=0.96 | None / wrong / hybrid_judge_downgrade |
