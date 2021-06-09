import argparse
import configparser
import re
import sys
from typing import Dict, Iterable, Optional, Tuple

def ask_choice(prompt, choices):
    if not choices:
        return None
    lowered_choices = [o.lower().strip() for o in choices]
    while True:
        print(f":: {prompt}")
        for i, option in enumerate(choices):
            print(f"   {i} {option}")
        answer = input("> ").strip().lower()
        if answer in lowered_choices:
            return answer
        try:
            if 0 <= int(answer) < len(choices):
                return choices[int(answer)]
        except:
            pass
        
def perform_subsitutions(text, variables):
    """Subsititues any occurances of ${NAME[:DEFAULT]} with the value from dictionary."""
    def evaluate_match(match):
        captures = match.groupdict()
        default = captures.get("default") or ""
        variable_name = captures.get("name") or ""
        if variable_name not in variables:
            return default
        return variables[variable_name]
    return re.sub(r"\$\{(?P<name>\w*):?(?P<default>.*?)\}",
                  evaluate_match,
                  text)


def parse_node_invocation(invocation: str) -> Tuple[str, Dict[str, str]]:
    """Parse a node invocation like `switch_on [(param:value), ...]` into node_id and the variable dict."""
    node_id_and_maybe_variables_text = re.split(
        r"\s+", invocation.strip(), maxsplit=1)
    node_id = node_id_and_maybe_variables_text[0]
    variables = {}
    if len(node_id_and_maybe_variables_text) == 2:
        variables_text = node_id_and_maybe_variables_text[1]
        for variable_text in re.finditer(r"\((?P<variable>[^()]+)\)", variables_text):
            name, value = variable_text.group("variable").split(":")
            variables[name] = value
    return (node_id, variables)


class Node():
    """Represents a node in the decision tree."""
    def __init__(self, node_id, text: str, root: Optional[bool] = False, **kwargs):
        self.node_id = node_id
        self.text = text
        self.root = False if root is None else bool(root)
        self.choice_to_node_invocation = {}
        for name, value in kwargs.items():
            branch_match = re.match(r"if_(?P<choice>\w+)", name, re.I)
            if not branch_match:
                continue
            choice = branch_match.groupdict().get("choice")
            if not choice:
                raise ValueError(
                    "A choice text cannot be empty, if_<x> must have a non-empty x")
            self.choice_to_node_invocation[choice] = value

    def run(self, variables: Dict[str, str]) -> Optional[Tuple[str, Dict[str, str]]]:
        """Run the node, returning the next node and invocation variables if any."""
        choices = []
        for choice, _ in self.choice_to_node_invocation.items():
            choices.append(choice)
        choices.append("exit")
        prompt = perform_subsitutions(self.text, variables)
        choice = ask_choice(prompt, choices=choices)
        if choice is None or choice == "exit":
            return None
        node_invocation = self.choice_to_node_invocation[choice]
        node_invocation = perform_subsitutions(node_invocation, variables)
        return parse_node_invocation(node_invocation)

    def __str__(self):
        return f"Node(id={self.node_id}, text={self.text}, root={self.root}, choices={self.choice_to_node_invocation})"


class Scenario():
    """Represents a collection of nodes for a troubleshooting scenario."""
    def __init__(self, config_file_obj: Iterable[str]):
        config_parser = configparser.ConfigParser()
        config_parser.read_file(config_file_obj)
        self.node_id_to_node = {}
        for node_id, settings in config_parser.items():
            if node_id == configparser.DEFAULTSECT:
                continue
            if settings.get("text") is None:
                raise ValueError("Each node must contain a text setting")
            self.node_id_to_node[node_id] = Node(node_id, **settings)

    def get_node(self, node_id: str) -> Node:
        if not re.match(r"\w+", node_id, re.I):
            raise ValueError(f"Invalid node id {node_id}")
        return self.node_id_to_node.get(node_id)

    def get_root_node_id(self) -> str:
        for id, node in self.node_id_to_node.items():
            if node.root == True:
                return id
        return None


class Troubleshooter():
    """Create a troubleshooter which uses the given scenario to help users."""
    def __init__(self, scenario: Scenario):
        self.scenario = scenario

    def get_help(self):
        node_id, variables = self.scenario.get_root_node_id(), {}
        if not node_id:
            raise Exception("No root node in scenario")
        while node_id is not None:
            node = self.scenario.get_node(node_id)
            if node is None:
                raise Exception(f"Node with id {node_id} could not be found")
            next = node.run(variables)
            if next is None:
                return "OK"
            node_id, variables = next


def main(argv=None):
    argv = argv or sys.argv[1:]
    parser = argparse.ArgumentParser("Troubleshooter")
    parser.add_argument("--scenario",
                        type=argparse.FileType("r"),
                        required=True)
    result = parser.parse_args(argv)
    troubleshooter = Troubleshooter(Scenario(result.scenario))
    troubleshooter.get_help()


if __name__ == "__main__":
    main()
