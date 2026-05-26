# think_parallel_v2 hybrid matcher audit

## Summary

- selected_judge_cases: `61`
- judged_pairs: `61`
- judge_errors: `0`

## Selection counts

| category | selected | judged |
|---|---:|---:|
| `argument_value_conflict` | 14 | 14 |
| `dependency_endpoint_unmatched` | 9 | 9 |
| `high_score_unmatched` | 7 | 7 |
| `schema_invalid_partial` | 27 | 27 |
| `semantic_tool_synonym_or_decomposition` | 18 | 18 |

## Cases

| case | categories | generated | candidate | judge | hybrid primary |
|---|---|---|---|---|---|
| multi_turn_base_143 t1 u1 | argument_value_conflict | `1. get_order_details(order_id=12345)` | h2: `get_order_details({"order_id": 12446})` | wrong c=0.98 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_143 t3 u1 | semantic_tool_synonym_or_decomposition | `1. get_account_details(username='USR001')` | h6: `send_message({"receiver_id": "USR003", "message": "My strategy is shifting due to recen...` | wrong c=0.96 | None / wrong / hybrid_p0 |
| multi_turn_base_143 t3 u2 | dependency_endpoint_unmatched,semantic_tool_synonym_or_decomposition | `2. notify_advisor(user_id='USR003', message="My strategy is shifting due to recent mark...` | h6: `send_message({"receiver_id": "USR003", "message": "My strategy is shifting due to recen...` | semantic c=0.90 | h6 / semantic / hybrid_judge_rescue |
| multi_turn_base_151 t0 u2 | semantic_tool_synonym_or_decomposition | `2. convert_currency(arg={"from_currency": "USD", "to_currency": "EUR"})` | h2: `compute_exchange_rate({"base_currency": "USD", "target_currency": "EUR", "value": 400.0})` | partial c=0.86 | h2 / partial / hybrid_judge_rescue |
| multi_turn_base_151 t0 u3 | semantic_tool_synonym_or_decomposition | `3. convert_currency(arg={"amount": "144756014165", "from_currency": "EUR", "to_currency...` | h2: `compute_exchange_rate({"base_currency": "USD", "target_currency": "EUR", "value": 400.0})` | wrong c=0.98 | None / wrong / hybrid_p0 |
| multi_turn_base_151 t1 u1 | semantic_tool_synonym_or_decomposition | `1. cancel_flight(booking_id='3426812', transaction_id='45451592')` | h4: `cancel_booking({"access_token": "abc123xyz", "booking_id": "3426812"})` | partial c=0.82 | h4 / partial / hybrid_judge_rescue |
| multi_turn_base_173 t1 u1 | semantic_tool_synonym_or_decomposition | `1. convert_currency(amount=2400.0, from_currency='USD', to_currency='USD')` | h2: `compute_exchange_rate({"base_currency": "USD", "target_currency": "GBP", "value": 2400.0})` | wrong c=0.94 | None / wrong / hybrid_p0 |
| multi_turn_base_173 t2 u1 | semantic_tool_synonym_or_decomposition | `1. verify_credit_card(access_token='abc123xyz', card_id='card_1496')` | h4: `book_flight({"access_token": "abc123xyz", "card_id": "card_1496", "travel_date": "2024-...` | wrong c=0.97 | None / wrong / hybrid_p0 |
| multi_turn_base_35 t0 u1 | dependency_endpoint_unmatched,semantic_tool_synonym_or_decomposition | `1. find_file(name="config.py")` | h3: `tail({"file_name": "config.py", "lines": 1})` | wrong c=0.94 | None / wrong / hybrid_p0 |
| multi_turn_base_35 t0 u2 | dependency_endpoint_unmatched,semantic_tool_synonym_or_decomposition | `2. read_file(file_name=$1.path, lines=1)` | h3: `tail({"file_name": "config.py", "lines": 1})` | partial c=0.68 | h3 / partial / hybrid_judge_rescue |
| multi_turn_base_35 t2 u4 | high_score_unmatched | `4. cat(file_name='diff.txt')` | h5: `diff({"file_name1": "config.py", "file_name2": "real_config.py"})` | wrong c=0.98 | None / wrong / hybrid_p0 |
| multi_turn_base_39 t2 u1 | high_score_unmatched | `1. ls(a=True)` | h9: `ls({})` | wrong c=0.96 | None / wrong / hybrid_p0 |
| multi_turn_base_55 t0 u1 | semantic_tool_synonym_or_decomposition | `1. checkFuelLevel()` | h1: `displayCarStatus({"_arg0": "fuel"})` | semantic c=0.86 | h1 / semantic / hybrid_judge_rescue |
| multi_turn_base_55 t0 u2 | argument_value_conflict,schema_invalid_partial | `1. fillFuelTank(arg=fuelAmount=20)` | h2: `fillFuelTank({"_arg0": 15.0})` | wrong c=0.95 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_55 t0 u3 | high_score_unmatched | `2. startEngine(arg=ignitionMode="START")` | h5: `startEngine({"ignitionMode": "START"})` | partial c=0.92 | h5 / partial / hybrid_judge_rescue |
| multi_turn_base_55 t0 u4 | high_score_unmatched | `3. startEngine(arg=ignitionMode="START")` | h5: `startEngine({"ignitionMode": "START"})` | partial c=0.86 | h5 / partial / hybrid_judge_rescue |
| multi_turn_base_55 t2 u1 | argument_value_conflict,schema_invalid_partial | `1. create_ticket(ticketTitle="Tire Pressure Issue", description="Urgent tire pressure i...` | h7: `create_ticket({"title": "Tire Pressure Issue", "description": "Urgent tire pressure iss...` | wrong c=0.95 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_55 t4 u2 | semantic_tool_synonym_or_decomposition | `2. update_ticket(ticket_id=2, description='Issue resolved!')` | h9: `resolve_ticket({"ticket_id": 2, "resolution": "Issue resolved!"})` | partial c=0.84 | None / wrong / hybrid_p0 |
| multi_turn_base_56 t1 u1 | argument_value_conflict | `1. fillFuelTank(fuelAmount=50.0)` | h5: `fillFuelTank({"fuelAmount": 40})` | wrong c=0.95 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_57 t0 u1 | dependency_endpoint_unmatched,semantic_tool_synonym_or_decomposition | `1. math.add(a=0.result, b=0.0)` | h1: `get_zipcode_based_on_city({"_arg0": "Crescent Hollow"})` | wrong c=0.97 | None / wrong / hybrid_p0 |
| multi_turn_base_59 t1 u1 | semantic_tool_synonym_or_decomposition | `1. get_fuel_level(vehicle_id='12345')` | h4: `displayCarStatus({"option": "fuel"})` | partial c=0.86 | h4 / partial / hybrid_judge_rescue |
| multi_turn_base_59 t3 u2 | semantic_tool_synonym_or_decomposition | `2. setIgnitionMode(mode='start')` | h9: `startEngine({"ignitionMode": "START"})` | semantic c=0.90 | h9 / semantic / hybrid_judge_rescue |
| multi_turn_base_62 t0 u1 | dependency_endpoint_unmatched | `1. get_zipcode_based_on_city(city=Rivermist)` | h1: `get_zipcode_based_on_city({"_arg0": "Rivermist"})` | exact c=0.98 | h1 / exact / hybrid_judge_override |
| multi_turn_base_62 t0 u2 | dependency_endpoint_unmatched | `2. get_zipcode_based_on_city(city=Stonebrook)` | h2: `get_zipcode_based_on_city({"_arg0": "Stonebrook"})` | exact c=0.98 | h2 / exact / hybrid_judge_override |
| multi_turn_base_62 t0 u4 | dependency_endpoint_unmatched,schema_invalid_partial | `4. send_message(receiver=Bob, message="The distance from Rivermist to Stonebrook is $3....` | h4: `send_message({"receiver_id": "USR002", "message": "The distance from Rivermist to Stone...` | partial c=0.86 | h4 / partial / hybrid_judge_override |
| multi_turn_base_62 t1 u1 | high_score_unmatched | `1. lockDoors(unlock=True, door=["driver", "passenger", "rear_left", "rear_right"])` | h5: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rear_right"]})` | wrong c=0.99 | None / wrong / hybrid_p0 |
| multi_turn_base_62 t1 u2 | argument_value_conflict | `2. lockDoors(unlock=True, door=["driver", "passenger", "rear_left", "rear_right"])` | h5: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rear_right"]})` | wrong c=0.99 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_62 t2 u1 | high_score_unmatched | `1. startEngine(ignitionMode='STOP')` | h7: `startEngine({"ignitionMode": "START"})` | wrong c=0.99 | None / wrong / hybrid_p0 |
| multi_turn_base_67 t1 u1 | semantic_tool_synonym_or_decomposition | `1. get_current_fuel_level()` | h4: `estimate_drive_feasibility_by_mileage({"distance": 780.0})` | wrong c=0.92 | None / wrong / hybrid_p0 |
| multi_turn_base_67 t1 u2 | semantic_tool_synonym_or_decomposition | `2. calculate_fuel_needed(distance=780.0)` | h4: `estimate_drive_feasibility_by_mileage({"distance": 780.0})` | partial c=0.82 | None / wrong / hybrid_p0 |
| multi_turn_base_67 t2 u1 | semantic_tool_synonym_or_decomposition | `1. get_fuel_level()` | h5: `fillFuelTank({"fuelAmount": 39.5})` | wrong c=0.96 | None / wrong / hybrid_p0 |
| multi_turn_base_67 t2 u2 | argument_value_conflict | `2. fillFuelTank(fuelAmount=20.0)` | h5: `fillFuelTank({"fuelAmount": 39.5})` | wrong c=0.98 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_70 t0 u1 | argument_value_conflict,schema_invalid_partial | `1. fillFuelTank(param={"fuelAmount": 38})` | h2: `fillFuelTank({"fuelAmount": 10})` | wrong c=0.96 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_70 t0 u2 | argument_value_conflict,schema_invalid_partial | `2. lockDoors(param={"unlock": True, "door": ["driver", "passenger", "rear_left", "rear_...` | h4: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rear_right"]})` | wrong c=0.98 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_71 t2 u2 | argument_value_conflict | `2. fillFuelTank(fuelAmount=50.0)` | h5: `fillFuelTank({"fuelAmount": 45.0})` | wrong c=0.98 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_86 t0 u1 | high_score_unmatched | `1. lockDoors(param={"unlock": True, "door": ["driver", "passenger", "rear_left", "rear_...` | h1: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rear_right"]})` | wrong c=0.98 | None / wrong / hybrid_p0 |
| multi_turn_base_86 t0 u2 | argument_value_conflict,schema_invalid_partial | `2. lockDoors(param={"unlock": True, "door": ["driver", "passenger", "rear_left", "rear_...` | h1: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rear_right"]})` | wrong c=0.99 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_86 t2 u1 | semantic_tool_synonym_or_decomposition | `1. send_tweet(content='Thank you to our vehicle for a smooth start!', hashtags='#Journe...` | h8: `post_tweet({"content": "Thank you to our vehicle for a smooth start!", "tags": ["#Journ...` | semantic c=0.94 | h8 / semantic / hybrid_judge_rescue |
| multi_turn_base_87 t0 u1 | argument_value_conflict,dependency_endpoint_unmatched | `1. gallon_to_liter(gallon=60)` | h1: `gallon_to_liter({"gallon": 60.0})` | partial c=0.88 | h1 / exact / hybrid_judge_confirm |
| multi_turn_base_87 t2 u1 | argument_value_conflict,schema_invalid_partial | `1. lockDoors(param={"unlock": True, "door": ["driver", "passenger", "rear_left", "rear_...` | h4: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rear_right"]})` | wrong c=0.98 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_88 t0 u1 | dependency_endpoint_unmatched | `1. gallon_to_liter(gallon=13.2)` | h1: `gallon_to_liter({"gallon": 13.2})` | exact c=0.99 | h1 / exact / hybrid_judge_override |
| multi_turn_base_88 t1 u1 | argument_value_conflict,schema_invalid_partial | `1. fillFuelTank(param={"fuelAmount": 49.967411999999996})` | h2: `fillFuelTank({"fuelAmount": 36.8})` | wrong c=0.95 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_88 t1 u3 | argument_value_conflict,schema_invalid_partial | `3. lockDoors(param={"unlock": True, "door": "all"})` | h3: `lockDoors({"unlock": false, "door": ["driver", "passenger", "rear_left", "rear_right"]})` | wrong c=0.98 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_143 t0 u1 | schema_invalid_partial | `1. add_to_watchlist(arg={"symbol": "ZETA"})` | h1: `add_to_watchlist({"stock": "ZETA"})` | partial c=0.91 | h1 / partial / hybrid_judge_override |
| multi_turn_base_151 t0 u1 | schema_invalid_partial | `1. get_flight_cost(arg={"travel_from": "San Francisco International", "travel_to": "Los...` | h1: `get_flight_cost({"travel_from": "SFO", "travel_to": "LAX", "travel_date": "2024-11-10",...` | partial c=0.89 | h1 / partial / hybrid_judge_override |
| multi_turn_base_151 t2 u2 | schema_invalid_partial | `2. post_tweet(hashtags=['TravelUpdate', 'BusinessTrip'], message='Just cancelled my tri...` | h6: `post_tweet({"content": "Just cancelled my trip to LA", "tags": ["#TravelUpdate", "#Busi...` | partial c=0.87 | h6 / partial / hybrid_judge_override |
| multi_turn_base_173 t1 u2 | schema_invalid_partial | `2. set_budget_limit(access_token='abc123xyz', budget_limit=10000, budget_currency='USD')` | h3: `set_budget_limit({"access_token": "abc123xyz", "budget_limit": 10000.0})` | partial c=0.90 | h3 / partial / hybrid_judge_override |
| multi_turn_base_185 t0 u1 | schema_invalid_partial | `1. get_flight_cost(travel_from="first airport",travel_to="second airport",travel_date="...` | h2: `get_flight_cost({"travel_from": "RMS", "travel_to": "SBK", "travel_date": "2024-12-15",...` | partial c=0.86 | h2 / partial / hybrid_judge_override |
| multi_turn_base_185 t1 u1 | schema_invalid_partial | `1. purchase_insurance(access_token='12345-67890', booking_id='d184e2c0-2ebb-4f39-a525-d...` | h4: `purchase_insurance({"access_token": "12345-67890", "insurance_type": "comprehensive", "...` | partial c=0.91 | h4 / partial / hybrid_judge_override |
| multi_turn_base_185 t2 u1 | schema_invalid_partial | `1. retrieve_invoice()` | h5: `retrieve_invoice({"access_token": "12345-67890", "booking_id": "d184e2c0-2ebb-4f39-a525...` | partial c=0.86 | h5 / partial / hybrid_judge_override |
| multi_turn_base_50 t0 u1 | schema_invalid_partial | `1. lockDoors(param={"unlock": True, "door": ["driver", "passenger", "rear_left", "rear_...` | h1: `lockDoors({"unlock": true, "door": ["driver", "passenger", "rear_left", "rear_right"]})` | partial c=0.96 | h1 / partial / hybrid_judge_override |
| multi_turn_base_50 t0 u2 | schema_invalid_partial | `2. setHeadlights(param={"mode": "on"})` | h2: `setHeadlights({"mode": "on"})` | partial c=0.95 | h2 / partial / hybrid_judge_override |
| multi_turn_base_55 t0 u5 | schema_invalid_partial | `3. startEngine(arg=ignitionMode="START")` | h5: `startEngine({"ignitionMode": "START"})` | partial c=0.90 | h5 / partial / hybrid_judge_override |
| multi_turn_base_55 t3 u1 | schema_invalid_partial | `1. get_ticket(id=2)` | h8: `get_ticket({"ticket_id": 2})` | partial c=0.93 | h8 / partial / hybrid_judge_override |
| multi_turn_base_56 t0 u2 | schema_invalid_partial | `2. get_zipcode_based_on_city(result=$1, field="zipcode")` | h2: `get_zipcode_based_on_city({"_arg0": "Rivermist"})` | wrong c=0.92 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_70 t0 u3 | schema_invalid_partial | `3. startEngine(param={"ignitionMode": "START"})` | h6: `startEngine({"ignitionMode": "START"})` | partial c=0.92 | h6 / partial / hybrid_judge_override |
| multi_turn_base_71 t0 u1 | schema_invalid_partial | `1. get_zipcode_based_on_city(arg={"city": "Rivermist"})` | h2: `get_zipcode_based_on_city({"_arg0": "Stonebrook"})` | wrong c=0.96 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_71 t0 u2 | schema_invalid_partial | `2. get_zipcode_based_on_city(arg={"city": "Stonebrook"})` | h1: `get_zipcode_based_on_city({"_arg0": "Rivermist"})` | wrong c=0.98 | None / wrong / hybrid_judge_downgrade |
| multi_turn_base_86 t0 u3 | schema_invalid_partial | `3. startEngine(param={"ignitionMode": "START"})` | h4: `startEngine({"ignitionMode": "START"})` | partial c=0.93 | h4 / partial / hybrid_judge_override |
| multi_turn_base_87 t2 u2 | schema_invalid_partial | `2. startEngine(param={"ignitionMode": "START"})` | h6: `startEngine({"ignitionMode": "START"})` | partial c=0.93 | h6 / partial / hybrid_judge_override |
| multi_turn_base_97 t0 u1 | schema_invalid_partial | `1. estimate_distance(arg={"city1": "Rivermist", "city2": "Stonebrook"})` | h3: `estimate_distance({"cityA": "83214", "cityB": "74532"})` | partial c=0.86 | h3 / partial / hybrid_judge_override |
