# think_parallel_v2 hybrid matcher audit

## Summary

- selected_judge_cases: `61`
- judged_pairs: `61`
- judge_errors: `0`

## Selection counts

| category | selected | judged |
|---|---:|---:|
| `argument_value_conflict` | 7 | 7 |
| `dependency_endpoint_unmatched` | 6 | 6 |
| `high_score_unmatched` | 10 | 10 |
| `schema_invalid_partial` | 25 | 25 |
| `semantic_tool_synonym_or_decomposition` | 17 | 17 |

## Cases

| case | categories | generated | candidate | judge | hybrid primary |
|---|---|---|---|---|---|
| multi_turn_base_143 t0 u1 | semantic_tool_synonym_or_decomposition | `2. add_stock_to_watchlist(symbol="ZETA")` | h1: `add_to_watchlist({"stock": "ZETA"})` | semantic c=0.95 | h1 / semantic / hybrid_judge_rescue |
| multi_turn_base_143 t1 u1 | argument_value_conflict | `1. get_order_details(order_id=12345)` | h2: `get_order_details({"order_id": 12446})` | wrong c=0.98 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_151 t0 u1 | high_score_unmatched | `1. get_flight_cost(access_token="abc123xyz", travel_from="SFO", travel_to="LAX", travel...` | h1: `get_flight_cost({"travel_from": "SFO", "travel_to": "LAX", "travel_date": "2024-11-10",...` | partial c=0.92 | h1 / partial / hybrid_judge_rescue |
| multi_turn_base_173 t1 u1 | semantic_tool_synonym_or_decomposition | `1. convert_currency(access_token='abc123xyz', amount=2400.0, from_currency='USD', to_cu...` | h3: `set_budget_limit({"access_token": "abc123xyz", "budget_limit": 10000.0})` | wrong c=0.96 | None / wrong / hybrid_p0 |
| multi_turn_base_173 t1 u2 | semantic_tool_synonym_or_decomposition | `2. convert_currency(access_token='abc123xyz', amount=10000.0, from_currency='USD', to_c...` | h3: `set_budget_limit({"access_token": "abc123xyz", "budget_limit": 10000.0})` | wrong c=0.94 | None / wrong / hybrid_p0 |
| multi_turn_base_173 t3 u2 | semantic_tool_synonym_or_decomposition | `2. cancel_ticket(access_token='abc123xyz', ticket_id='ticket_001', reason='Unnecessary ...` | h5: `close_ticket({"ticket_id": "ticket_001"})` | semantic c=0.88 | h5 / semantic / hybrid_judge_rescue |
| multi_turn_base_35 t0 u1 | dependency_endpoint_unmatched,semantic_tool_synonym_or_decomposition | `1. find_file(name="config.py")` | h3: `tail({"file_name": "config.py", "lines": 1})` | wrong c=0.95 | None / wrong / hybrid_p0 |
| multi_turn_base_35 t0 u2 | dependency_endpoint_unmatched,semantic_tool_synonym_or_decomposition | `2. read_file(file_name=$1, lines=1)` | h3: `tail({"file_name": "config.py", "lines": 1})` | partial c=0.72 | None / wrong / hybrid_p0 |
| multi_turn_base_35 t0 u4 | dependency_endpoint_unmatched,semantic_tool_synonym_or_decomposition | `4. read_file(file_name=$3, lines=1)` | h3: `tail({"file_name": "config.py", "lines": 1})` | partial c=0.74 | h3 / partial / hybrid_judge_rescue |
| multi_turn_base_35 t2 u2 | high_score_unmatched | `2. cat(file_name='diff.txt')` | h5: `diff({"file_name1": "config.py", "file_name2": "real_config.py"})` | wrong c=0.98 | None / wrong / hybrid_p0 |
| multi_turn_base_39 t2 u2 | high_score_unmatched | `2. ls(file_name='styles.css')` | h9: `ls({})` | wrong c=0.93 | None / wrong / hybrid_p0 |
| multi_turn_base_39 t2 u3 | high_score_unmatched | `3. ls(file_name='script.js')` | h9: `ls({})` | wrong c=0.91 | None / wrong / hybrid_p0 |
| multi_turn_base_55 t0 u1 | semantic_tool_synonym_or_decomposition | `1. checkFuelLevel(fuelAmount=15.0)` | h1: `displayCarStatus({"_arg0": "fuel"})` | partial c=0.78 | h1 / partial / hybrid_judge_rescue |
| multi_turn_base_55 t4 u1 | semantic_tool_synonym_or_decomposition | `2. update_ticket(ticket_id=2, title='Tire Pressure Issue', description='Issue resolved!')` | h9: `resolve_ticket({"ticket_id": 2, "resolution": "Issue resolved!"})` | partial c=0.82 | None / wrong / hybrid_p0 |
| multi_turn_base_56 t1 u2 | argument_value_conflict | `2. fillFuelTank(fuelAmount=50.0)` | h5: `fillFuelTank({"fuelAmount": 40})` | wrong c=0.98 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_57 t1 u1 | high_score_unmatched | `1. logarithm(value=630.0, base=10, precision=5)` | h4: `logarithm({"value": 630.0, "base": 10, "precision": 5})` | exact c=1.00 | h4 / exact / hybrid_judge_rescue |
| multi_turn_base_59 t1 u1 | semantic_tool_synonym_or_decomposition | `1. get_vehicle_status(field='fuelLevel')` | h4: `displayCarStatus({"option": "fuel"})` | semantic c=0.86 | h4 / semantic / hybrid_judge_rescue |
| multi_turn_base_59 t2 u2 | semantic_tool_synonym_or_decomposition | `2. updateFuelLevel(fuelAmount=50.0)` | h6: `fillFuelTank({"fuelAmount": 40})` | wrong c=0.92 | None / wrong / hybrid_p0 |
| multi_turn_base_62 t0 u1 | semantic_tool_synonym_or_decomposition | `1. get_navigation(arg={"destination": "Stonebrook"})` | h4: `send_message({"receiver_id": "USR002", "message": "The distance from Rivermist to Stone...` | wrong c=0.98 | None / wrong / hybrid_p0 |
| multi_turn_base_62 t0 u2 | semantic_tool_synonym_or_decomposition | `2. get_navigation(arg={"destination": "Rivermist"})` | h1: `get_zipcode_based_on_city({"_arg0": "Rivermist"})` | wrong c=0.90 | None / wrong / hybrid_p0 |
| multi_turn_base_62 t0 u3 | semantic_tool_synonym_or_decomposition | `3. format_message(arg={"message": "The distance from Rivermist to Stonebrook is $distan...` | h4: `send_message({"receiver_id": "USR002", "message": "The distance from Rivermist to Stone...` | partial c=0.86 | None / wrong / hybrid_p0 |
| multi_turn_base_67 t0 u1 | high_score_unmatched | `1. get_zipcode_based_on_city(arg={"city": "San Francisco"})` | h1: `get_zipcode_based_on_city({"_arg0": "San Francisco"})` | partial c=0.93 | h1 / partial / hybrid_judge_rescue |
| multi_turn_base_67 t0 u2 | high_score_unmatched | `2. get_zipcode_based_on_city(arg={"city": "Silverpine"})` | h2: `get_zipcode_based_on_city({"_arg0": "Silverpine"})` | partial c=0.95 | h2 / partial / hybrid_judge_rescue |
| multi_turn_base_67 t0 u3 | semantic_tool_synonym_or_decomposition | `3. calculate_distance_between_cities(arg={"city1": "San Francisco", "city2": "Silverpin...` | h1: `get_zipcode_based_on_city({"_arg0": "San Francisco"})` | wrong c=0.96 | None / wrong / hybrid_p0 |
| multi_turn_base_67 t2 u2 | argument_value_conflict | `2. fillFuelTank(fuelAmount=20.0)` | h5: `fillFuelTank({"fuelAmount": 39.5})` | wrong c=0.98 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_67 t3 u1 | semantic_tool_synonym_or_decomposition | `1. get_engine_state()` | h8: `startEngine({"ignitionMode": "START"})` | wrong c=0.94 | None / wrong / hybrid_p0 |
| multi_turn_base_70 t0 u1 | argument_value_conflict,schema_invalid_partial | `1. fillFuelTank(param={"fuelAmount": 38.0})` | h2: `fillFuelTank({"fuelAmount": 10})` | wrong c=0.96 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_71 t0 u2 | high_score_unmatched | `2. get_zipcode_based_on_city(arg={"city": "Stonebrook"})` | h2: `get_zipcode_based_on_city({"_arg0": "Stonebrook"})` | partial c=0.93 | h2 / partial / hybrid_judge_rescue |
| multi_turn_base_71 t2 u1 | argument_value_conflict | `1. fillFuelTank(fuelAmount=20.0)` | h5: `fillFuelTank({"fuelAmount": 45.0})` | wrong c=0.96 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_71 t4 u1 | high_score_unmatched | `1. set_navigation(destination='Crescent Hollow, Spring, TX')` | h9: `set_navigation({"destination": "Crescent Hollow, Spring, TX"})` | exact c=0.98 | h9 / exact / hybrid_judge_rescue |
| multi_turn_base_87 t0 u1 | dependency_endpoint_unmatched | `1. gallon_to_liter(gallon=60.0)` | h1: `gallon_to_liter({"gallon": 60.0})` | exact c=0.98 | h1 / exact / hybrid_judge_override |
| multi_turn_base_87 t2 u2 | argument_value_conflict | `2. lockDoors(unlock=True, door=["driver", "passenger", "rear_left", "rear_right"])` | h4: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rear_right"]})` | wrong c=0.99 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_88 t0 u1 | dependency_endpoint_unmatched | `1. gallon_to_liter(gallon=13.2)` | h1: `gallon_to_liter({"gallon": 13.2})` | exact c=0.99 | h1 / exact / hybrid_judge_override |
| multi_turn_base_91 t0 u1 | dependency_endpoint_unmatched | `1. get_outside_temperature_from_google()` | h1: `get_outside_temperature_from_google({})` | exact c=0.99 | h1 / exact / hybrid_judge_override |
| multi_turn_base_97 t2 u1 | argument_value_conflict | `1. fillFuelTank(fuelAmount=10.0)` | h5: `fillFuelTank({"fuelAmount": 45.0})` | wrong c=0.98 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_97 t3 u1 | high_score_unmatched | `1. startEngine(arg={"ignitionMode": "START"})` | h8: `startEngine({"ignitionMode": "START"})` | partial c=0.91 | h8 / partial / hybrid_judge_rescue |
| multi_turn_base_97 t4 u1 | semantic_tool_synonym_or_decomposition | `1. generate_message(message="I am on my way")` | h9: `send_message({"receiver_id": "BD732D1888B94DAA", "message": "I am on my way."})` | partial c=0.93 | None / wrong / hybrid_p0 |
| multi_turn_base_151 t0 u2 | schema_invalid_partial | `2. get_flight_cost(access_token="abc123xyz", travel_from="SFO", travel_to="LAX", travel...` | h1: `get_flight_cost({"travel_from": "SFO", "travel_to": "LAX", "travel_date": "2024-11-10",...` | partial c=0.92 | h1 / partial / hybrid_judge_override |
| multi_turn_base_151 t2 u2 | schema_invalid_partial | `2. post_tweet(username="john", content="Just canceled my trip to LA. #TravelUpdate #Bus...` | h6: `post_tweet({"content": "Just cancelled my trip to LA", "tags": ["#TravelUpdate", "#Busi...` | partial c=0.86 | h6 / partial / hybrid_judge_override |
| multi_turn_base_185 t0 u1 | schema_invalid_partial | `1. get_flight_cost(param=access_token=12345-67890,travel_from=SFO,travel_to=LAX,travel_...` | h2: `get_flight_cost({"travel_from": "RMS", "travel_to": "SBK", "travel_date": "2024-12-15",...` | wrong c=0.92 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_185 t0 u2 | schema_invalid_partial | `2. set_budget_limit(param=access_token=12345-67890,budget_limit=2000.0)` | h3: `set_budget_limit({"access_token": "12345-67890", "budget_limit": 2000.0})` | partial c=0.94 | h3 / partial / hybrid_judge_override |
| multi_turn_base_185 t1 u1 | schema_invalid_partial | `1. purchase_insurance(access_token='12345-67890', booking_id='d184e2c0-2ebb-4f39-a525-d...` | h4: `purchase_insurance({"access_token": "12345-67890", "insurance_type": "comprehensive", "...` | partial c=0.94 | h4 / partial / hybrid_judge_override |
| multi_turn_base_35 t2 u1 | schema_invalid_partial | `1. diff(file1='config.py', file2='real_config.py', output_name='diff.txt')` | h5: `diff({"file_name1": "config.py", "file_name2": "real_config.py"})` | partial c=0.86 | h5 / partial / hybrid_judge_confirm |
| multi_turn_base_39 t2 u4 | schema_invalid_partial | `4. ls(file_name='index.html')` | h9: `ls({})` | partial c=0.86 | h9 / partial / hybrid_judge_confirm |
| multi_turn_base_50 t0 u1 | schema_invalid_partial | `1. lockDoors(param={"unlock": True, "door": ["driver", "passenger", "rear_left", "front...` | h1: `lockDoors({"unlock": true, "door": ["driver", "passenger", "rear_left", "rear_right"]})` | wrong c=0.93 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_50 t0 u2 | schema_invalid_partial | `2. setHeadlights(param={"mode": "on"})` | h2: `setHeadlights({"mode": "on"})` | partial c=0.95 | h2 / partial / hybrid_judge_override |
| multi_turn_base_55 t3 u1 | schema_invalid_partial | `1. get_ticket(id=2)` | h8: `get_ticket({"ticket_id": 2})` | partial c=0.92 | h8 / partial / hybrid_judge_override |
| multi_turn_base_56 t0 u1 | schema_invalid_partial | `1. get_zipcode_based_on_city(arg=city="Sun San Francisco")` | h1: `get_zipcode_based_on_city({"_arg0": "San Francisco"})` | wrong c=0.93 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_56 t0 u2 | schema_invalid_partial | `2. get_zipcode_based_on_city(arg=city="Rivermist")` | h2: `get_zipcode_based_on_city({"_arg0": "Rivermist"})` | partial c=0.94 | h2 / partial / hybrid_judge_override |
| multi_turn_base_59 t3 u1 | schema_invalid_partial | `1. startEngine(operation='start')` | h9: `startEngine({"ignitionMode": "START"})` | partial c=0.86 | h9 / partial / hybrid_judge_override |
| multi_turn_base_62 t0 u4 | schema_invalid_partial | `4. send_message(arg={"user_name": "Bob", "user_id": "USR002"})` | h4: `send_message({"receiver_id": "USR002", "message": "The distance from Rivermist to Stone...` | partial c=0.91 | h4 / partial / hybrid_judge_confirm |
| multi_turn_base_62 t1 u1 | schema_invalid_partial | `1. lockDoors(lockStatus={"driver": "locked", "passenger": "locked", "rear_left": "locke...` | h5: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rear_right"]})` | partial c=0.91 | h5 / partial / hybrid_judge_override |
| multi_turn_base_67 t0 u4 | schema_invalid_partial | `4. get_zipcode_based_on_city(arg={"city": "San Francisco"})` | h1: `get_zipcode_based_on_city({"_arg0": "San Francisco"})` | partial c=0.94 | h1 / partial / hybrid_judge_override |
| multi_turn_base_67 t0 u5 | schema_invalid_partial | `5. get_zipcode_based_on_city(arg={"city": "Silverpine"})` | h2: `get_zipcode_based_on_city({"_arg0": "Silverpine"})` | partial c=0.91 | h2 / partial / hybrid_judge_override |
| multi_turn_base_70 t0 u2 | schema_invalid_partial | `2. startEngine(param={"ignitionMode": "START"})` | h6: `startEngine({"ignitionMode": "START"})` | partial c=0.94 | h6 / partial / hybrid_judge_override |
| multi_turn_base_71 t0 u1 | schema_invalid_partial | `1. get_zipcode_based_on_city(arg={"city": "Rivermist"})` | h1: `get_zipcode_based_on_city({"_arg0": "Rivermist"})` | partial c=0.92 | h1 / partial / hybrid_judge_override |
| multi_turn_base_71 t0 u4 | schema_invalid_partial | `4. get_zipcode_based_on_city(arg={"city": "Rivermist, Stonebrook"})` | h2: `get_zipcode_based_on_city({"_arg0": "Stonebrook"})` | partial c=0.86 | h2 / partial / hybrid_judge_confirm |
| multi_turn_base_86 t2 u1 | schema_invalid_partial | `1. post_tweet(content="Thank you to our vehicle for a smooth start!", hashtags=[["#Jour...` | h8: `post_tweet({"content": "Thank you to our vehicle for a smooth start!", "tags": ["#Journ...` | partial c=0.88 | h8 / partial / hybrid_judge_override |
| multi_turn_base_88 t1 u2 | schema_invalid_partial | `2. lockDoors(door=["driver", "passenger"])` | h3: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rear_right"]})` | partial c=0.95 | h3 / partial / hybrid_judge_confirm |
| multi_turn_base_97 t3 u2 | schema_invalid_partial | `2. startEngine(arg={"ignitionMode": "START"})` | h8: `startEngine({"ignitionMode": "START"})` | partial c=0.93 | h8 / partial / hybrid_judge_override |
| multi_turn_base_97 t4 u2 | schema_invalid_partial | `2. send_message(to="Michael", message="I am on my way")` | h9: `send_message({"receiver_id": "BD732D1888B94DAA", "message": "I am on my way."})` | partial c=0.87 | h9 / partial / hybrid_judge_override |
