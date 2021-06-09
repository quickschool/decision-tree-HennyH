import os
import json
from bottle import route, post, run, abort, request, static_file
from troubleshooter import Scenario, perform_subsitutions, parse_node_invocation

@route("/")
def index():
    return static_file("index.html", root=".")

@post("/scenarios/nodes")
def get_secnario_node():
    data = json.load(request.body)
    if "scenario_filename" not in data:
        abort(400, "The field 'scenario_filename' must be present in the json request")            
    scenario_filename = data["scenario_filename"] 
    node_id = data.get("node_id", None)
    variables = data.get("variables", {})
    if not os.path.exists(scenario_filename):
        abort(404, f"scenario file {scenario_filename} not found")
    with open(scenario_filename, "r") as scenario_fileobj:
        scenario = Scenario(scenario_fileobj)
        node = \
            scenario.get_node(scenario.get_root_node_id()) \
            if node_id is None \
            else scenario.get_node(node_id)
        if node is None:
            abort(404, f"No such node {node_id} exists in the {scenario_filename} scenario")
        result = {
            "node_id": node.node_id,
            "prompt": perform_subsitutions(node.text, variables),
            "choices": []
        }
        for choice, node_invocation in node.choice_to_node_invocation.items():
            next_node_id, next_variables = \
                parse_node_invocation(perform_subsitutions(node_invocation, variables))
            choice = {
                "text": perform_subsitutions(choice, variables),
                "next_node_id": next_node_id,
                "next_variables": next_variables
            }
            result["choices"].append(choice)
        return result

if __name__ == "__main__":
    run(host="localhost", port=8080, debug=True)
