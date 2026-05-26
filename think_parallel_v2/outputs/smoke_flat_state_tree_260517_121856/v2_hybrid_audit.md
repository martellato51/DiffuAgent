# think_parallel_v2 hybrid matcher audit

## Summary

- selected_judge_cases: `52`
- judged_pairs: `52`
- judge_errors: `0`

## Selection counts

| category | selected | judged |
|---|---:|---:|
| `argument_value_conflict` | 10 | 10 |
| `dependency_endpoint_unmatched` | 1 | 1 |
| `high_score_unmatched` | 4 | 4 |
| `schema_invalid_partial` | 17 | 17 |
| `semantic_tool_synonym_or_decomposition` | 22 | 22 |

## Cases

| case | categories | generated | candidate | judge | hybrid primary |
|---|---|---|---|---|---|
| multi_turn_base_143 t0 u1 | semantic_tool_synonym_or_decomposition | `1. add_stock_to_watchlist(symbol="ZETA")` | h1: `add_to_watchlist({"stock": "ZETA"})` | semantic c=0.93 | h1 / semantic / hybrid_judge_rescue |
| multi_turn_base_143 t1 u1 | argument_value_conflict | `1. get_order_details(order_id=12345)` | h2: `get_order_details({"order_id": 12446})` | wrong c=0.98 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_143 t3 u2 | dependency_endpoint_unmatched,semantic_tool_synonym_or_decomposition | `2. notify_advisor(user_id="USR003", message="My strategy is shifting due to recent mark...` | h6: `send_message({"receiver_id": "USR003", "message": "My strategy is shifting due to recen...` | semantic c=0.90 | h6 / semantic / hybrid_judge_rescue |
| multi_turn_base_151 t0 u2 | semantic_tool_synonym_or_decomposition | `2. convert_currency(arg={"access_token": "abc123xyz", "card_id": "144756014165", "amoun...` | h3: `book_flight({"access_token": "abc123xyz", "card_id": "144756014165", "travel_date": "20...` | wrong c=0.96 | None / wrong / hybrid_p0 |
| multi_turn_base_173 t1 u1 | semantic_tool_synonym_or_decomposition | `1. convert_currency(access_token='abc123xyz', amount=2400.0, from_currency='USD', to_cu...` | h3: `set_budget_limit({"access_token": "abc123xyz", "budget_limit": 10000.0})` | wrong c=0.95 | None / wrong / hybrid_p0 |
| multi_turn_base_173 t1 u2 | semantic_tool_synonym_or_decomposition | `2. convert_currency(access_token='abc123xyz', amount=10000.0, from_currency='USD', to_c...` | h3: `set_budget_limit({"access_token": "abc123xyz", "budget_limit": 10000.0})` | wrong c=0.92 | None / wrong / hybrid_p0 |
| multi_turn_base_173 t2 u1 | semantic_tool_synonym_or_decomposition | `1. get_credit_card_details(access_token='abc123xyz', card_id='card_1496')` | h4: `book_flight({"access_token": "abc123xyz", "card_id": "card_1496", "travel_date": "2024-...` | wrong c=0.96 | None / wrong / hybrid_p0 |
| multi_turn_base_173 t3 u2 | semantic_tool_synonym_or_decomposition | `2. cancel_ticket(ticket_id='ticket_001', booking_id='booking_001')` | h5: `close_ticket({"ticket_id": "ticket_001"})` | semantic c=0.88 | h5 / semantic / hybrid_judge_rescue |
| multi_turn_base_35 t2 u4 | high_score_unmatched | `4. cat(file_name='diff.txt')` | h5: `diff({"file_name1": "config.py", "file_name2": "real_config.py"})` | wrong c=0.98 | None / wrong / hybrid_p0 |
| multi_turn_base_39 t2 u2 | high_score_unmatched | `2. ls(file_name='index.html')` | h9: `ls({})` | wrong c=0.93 | None / wrong / hybrid_p0 |
| multi_turn_base_55 t0 u1 | semantic_tool_synonym_or_decomposition | `1. checkFuelLevel(arg={"option": "fuel"})` | h1: `displayCarStatus({"_arg0": "fuel"})` | semantic c=0.90 | h1 / semantic / hybrid_judge_rescue |
| multi_turn_base_55 t0 u2 | semantic_tool_synonym_or_decomposition | `2. checkFuelLevel(arg={"option": "fuel"})` | h1: `displayCarStatus({"_arg0": "fuel"})` | semantic c=0.88 | h1 / semantic / hybrid_judge_rescue |
| multi_turn_base_55 t0 u3 | semantic_tool_synonym_or_decomposition | `3. checkFuelLevel(arg={"option": "fuel"})` | h1: `displayCarStatus({"_arg0": "fuel"})` | semantic c=0.92 | h1 / semantic / hybrid_judge_rescue |
| multi_turn_base_55 t0 u4 | semantic_tool_synonym_or_decomposition | `4. addFuel(arg={"option": "fuel", "amount": 10.0})` | h1: `displayCarStatus({"_arg0": "fuel"})` | wrong c=0.93 | None / wrong / hybrid_p0 |
| multi_turn_base_55 t4 u1 | semantic_tool_synonym_or_decomposition | `1. update_ticket(ticket_id=2, title='Tire Pressure Issue', description='Issue resolved!')` | h9: `resolve_ticket({"ticket_id": 2, "resolution": "Issue resolved!"})` | partial c=0.86 | h9 / partial / hybrid_judge_rescue |
| multi_turn_base_56 t1 u1 | semantic_tool_synonym_or_decomposition | `1. checkFuelLevel()` | h4: `displayCarStatus({"_arg0": "fuel"})` | semantic c=0.90 | h4 / semantic / hybrid_judge_rescue |
| multi_turn_base_56 t1 u2 | argument_value_conflict | `2. fillFuelTank(fuelAmount=40.0)` | h5: `fillFuelTank({"fuelAmount": 40})` | exact c=0.98 | h5 / exact / hybrid_judge_override |
| multi_turn_base_56 t2 u1 | argument_value_conflict | `1. lockDoors(unlock=True, door=['driver', 'passenger', 'rear_left', 'rear_right'])` | h6: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rear_right"]})` | wrong c=0.98 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_59 t1 u1 | semantic_tool_synonym_or_decomposition | `1. get_fuel_level(param='fuelLevel')` | h4: `displayCarStatus({"option": "fuel"})` | semantic c=0.88 | h4 / semantic / hybrid_judge_rescue |
| multi_turn_base_59 t2 u2 | semantic_tool_synonym_or_decomposition | `2. updateFuelLevel(fuelAmount=50.0)` | h6: `fillFuelTank({"fuelAmount": 40})` | wrong c=0.91 | None / wrong / hybrid_p0 |
| multi_turn_base_59 t3 u1 | semantic_tool_synonym_or_decomposition | `1. getIgnitionMode(mode="start")` | h9: `startEngine({"ignitionMode": "START"})` | partial c=0.74 | h9 / partial / hybrid_judge_rescue |
| multi_turn_base_59 t3 u2 | semantic_tool_synonym_or_decomposition | `2. setIgnitionMode(mode="start")` | h9: `startEngine({"ignitionMode": "START"})` | semantic c=0.88 | h9 / semantic / hybrid_judge_rescue |
| multi_turn_base_62 t0 u1 | semantic_tool_synonym_or_decomposition | `1. get_navigation(arg={"destination": "Stonebrook"})` | h4: `send_message({"receiver_id": "USR002", "message": "The distance from Rivermist to Stone...` | wrong c=0.94 | None / wrong / hybrid_p0 |
| multi_turn_base_62 t1 u1 | high_score_unmatched | `1. lockDoors(unlock=True, door=["driver", "passenger", "rear_left", "rear_right"])` | h5: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rear_right"]})` | wrong c=0.99 | None / wrong / hybrid_p0 |
| multi_turn_base_62 t1 u2 | high_score_unmatched | `2. lockDoors(unlock=True, door=["front_left", "passenger"])` | h5: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rear_right"]})` | wrong c=0.98 | None / wrong / hybrid_p0 |
| multi_turn_base_62 t1 u3 | argument_value_conflict | `3. lockDoors(unlock=True, door=["driver", "passenger", "rear_left", "rear_right"])` | h5: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rear_right"]})` | wrong c=0.99 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_67 t0 u3 | semantic_tool_synonym_or_decomposition | `3. estimate_distance_between_cities(city1="San Francisco", city2="Silverpine", zipcode1...` | h1: `get_zipcode_based_on_city({"_arg0": "San Francisco"})` | wrong c=0.93 | None / wrong / hybrid_p0 |
| multi_turn_base_67 t2 u1 | argument_value_conflict | `1. fillFuelTank(fuelAmount=20.0)` | h5: `fillFuelTank({"fuelAmount": 39.5})` | wrong c=0.98 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_70 t0 u1 | argument_value_conflict,schema_invalid_partial | `1. fillFuelTank({"fuelAmount": 38.0})` | h2: `fillFuelTank({"fuelAmount": 10})` | wrong c=0.96 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_70 t1 u2 | semantic_tool_synonym_or_decomposition | `2. navigateToDestination(destination="Tire Service Center, Main Street, City, State")` | h9: `set_navigation({"destination": "456 Oakwood Avenue, Rivermist, 83214"})` | wrong c=0.92 | None / wrong / hybrid_p0 |
| multi_turn_base_71 t2 u1 | semantic_tool_synonym_or_decomposition | `1. getFuelAmount(fuelAmount=15.0)` | h5: `fillFuelTank({"fuelAmount": 45.0})` | wrong c=0.93 | None / wrong / hybrid_p0 |
| multi_turn_base_71 t2 u2 | argument_value_conflict | `2. fillFuelTank(fuelAmount=15.0)` | h5: `fillFuelTank({"fuelAmount": 45.0})` | wrong c=0.98 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_86 t0 u1 | argument_value_conflict | `1. lockDoors(unlock=True, door=["driver", "passenger", "rear_left", "rear_right"])` | h1: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rear_right"]})` | wrong c=0.99 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_87 t2 u2 | argument_value_conflict | `2. lockDoors(unlock=True, door=["driver", "passenger", "rear_left", "rear_right"])` | h4: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rear_right"]})` | wrong c=0.99 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_91 t0 u1 | semantic_tool_synonym_or_decomposition | `1. get_outside_temperature()` | h2: `send_message({"receiver_id": "USR006", "message": "It is hot outside."})` | wrong c=0.96 | None / wrong / hybrid_p0 |
| multi_turn_base_97 t2 u1 | argument_value_conflict | `1. fillFuelTank(fuelAmount=10.0)` | h5: `fillFuelTank({"fuelAmount": 45.0})` | wrong c=0.98 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_143 t3 u1 | schema_invalid_partial | `1. get_account_info(account_id=12345)` | h5: `get_account_info({})` | partial c=0.90 | h5 / partial / hybrid_judge_override |
| multi_turn_base_151 t0 u1 | schema_invalid_partial | `1. get_flight_cost(arg={"travel_from": "San Francisco", "travel_to": "Los Angeles", "tr...` | h1: `get_flight_cost({"travel_from": "SFO", "travel_to": "LAX", "travel_date": "2024-11-10",...` | partial c=0.87 | h1 / partial / hybrid_judge_override |
| multi_turn_base_151 t2 u2 | schema_invalid_partial | `2. post_tweet(hashtags=['#TravelUpdate', '#BusinessTrip'], message='Just cancelled my t...` | h6: `post_tweet({"content": "Just cancelled my trip to LA", "tags": ["#TravelUpdate", "#Busi...` | partial c=0.93 | h6 / partial / hybrid_judge_override |
| multi_turn_base_185 t1 u1 | schema_invalid_partial | `1. purchase_insurance(access_token='12345-67890', booking_id='d184e2c0-2ebb-4f39-a525-d...` | h4: `purchase_insurance({"access_token": "12345-67890", "insurance_type": "comprehensive", "...` | partial c=0.93 | h4 / partial / hybrid_judge_override |
| multi_turn_base_39 t2 u1 | schema_invalid_partial | `1. ls(file_name='styles.css')` | h9: `ls({})` | partial c=0.82 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_50 t0 u1 | schema_invalid_partial | `1. lockDoors(arg={"unlock": True, "door": ["driver", "passenger", "rear_left", "rear_ri...` | h1: `lockDoors({"unlock": true, "door": ["driver", "passenger", "rear_left", "rear_right"]})` | partial c=0.95 | h1 / partial / hybrid_judge_override |
| multi_turn_base_50 t0 u2 | schema_invalid_partial | `2. setHeadlights(arg={"mode": "on"})` | h2: `setHeadlights({"mode": "on"})` | partial c=0.94 | h2 / partial / hybrid_judge_override |
| multi_turn_base_55 t0 u6 | schema_invalid_partial | `6. startEngine(arg={"ignitionMode": "START"})` | h5: `startEngine({"ignitionMode": "START"})` | partial c=0.95 | h5 / partial / hybrid_judge_override |
| multi_turn_base_55 t3 u1 | schema_invalid_partial | `1. get_ticket(id=2)` | h8: `get_ticket({"ticket_id": 2})` | partial c=0.93 | h8 / partial / hybrid_judge_override |
| multi_turn_base_56 t0 u1 | schema_invalid_partial | `1. get_zipcode_based_on_city(city=<zipcode for San Francisco>)` | h1: `get_zipcode_based_on_city({"_arg0": "San Francisco"})` | partial c=0.86 | h1 / partial / hybrid_judge_override |
| multi_turn_base_56 t0 u2 | schema_invalid_partial | `2. get_zipcode_based_on_city(city=<zipcode for Rivermist>)` | h2: `get_zipcode_based_on_city({"_arg0": "Rivermist"})` | partial c=0.78 | h2 / partial / hybrid_judge_override |
| multi_turn_base_87 t0 u1 | schema_invalid_partial | `1. gallon_to_liter({ "gallon": 60.0})` | h1: `gallon_to_liter({"gallon": 60.0})` | partial c=0.95 | h1 / partial / hybrid_judge_override |
| multi_turn_base_88 t2 u2 | schema_invalid_partial | `2. post_tweet(content="Embarking on an exciting road trip from SF to Rivermist! #RoadTr...` | h7: `post_tweet({"content": "Embarking on an exciting road trip from SF to Rivermist!", "tag...` | partial c=0.92 | h7 / partial / hybrid_judge_override |
| multi_turn_base_91 t0 u2 | schema_invalid_partial | `2. send_message(user_id="Michael", message="It is hot outside.")` | h2: `send_message({"receiver_id": "USR006", "message": "It is hot outside."})` | partial c=0.92 | h2 / partial / hybrid_judge_override |
| multi_turn_base_97 t3 u1 | schema_invalid_partial | `1. startEngine(arg={"ignitionMode": "START"})` | h8: `startEngine({"ignitionMode": "START"})` | partial c=0.93 | h8 / partial / hybrid_judge_override |
| multi_turn_base_97 t4 u1 | schema_invalid_partial | `1. send_message(toUser="Michael", message="I am on my way")` | h9: `send_message({"receiver_id": "BD732D1888B94DAA", "message": "I am on my way."})` | partial c=0.86 | h9 / partial / hybrid_judge_override |
