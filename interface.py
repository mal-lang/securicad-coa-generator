from securicad.session import Session
from securicad.user import User
from securicad.coagen import CoAGenerator
import sys
import warnings

# suppressing HTTPS insecure connection warnings
suppress = True
if suppress and not sys.warnoptions:
    warnings.simplefilter("ignore")

def main(argument):
    '''
    usage: in the command line, type
        python interface.py <inputfile>

    <inputfile> should be a .txt file formatted as follows
        <ip_addres>
        <username>
        <password>
        <project_id>
        <model_id>
        <target objects' ids, separated by commas>
        <criticality metrics to be used for generating CoAs, separated by commas; valid values are f, o, fo, and of>
        <limit on the number of simulations performed per CoA>
        <minimal number of defenses added to a CoA per iteration>

    see 'interface_example_input.txt' for an example. this if of course far from the final version.
    '''
    if type(argument) == type([]):
        input_path = argv[0]
    input_path = argument
    with open(input_path, 'r') as f:
        inputs = [line.strip() for line in f.readlines()]
        ip_addres = inputs[0]
        username = inputs[1]
        password = inputs[2]
        project_id = inputs[3]
        model_id = inputs[4]
        target_objects_ids = [item.strip() for item in inputs[5].split(',')]
        criticality_metrics = [item.strip() for item in inputs[6].split(',')]
        iters = int(inputs[7])
        defs_per_iter = int(inputs[8])

    user = User(name=username, password=password)
    session = Session(ip_address=ip_addres, user=user)

    generator = CoAGenerator(session)

    result = generator.generate_coas(project_id=project_id, model_id=model_id,
                                     target_objects_ids=target_objects_ids,
                                     crit_metrics=criticality_metrics, iterations_number_limit=iters, defs_per_iteration=defs_per_iter)

    for item in result:
        print(item)
    return

if __name__ == '__main__':
    #main(sys.argv[1:])
    main('interface_example_input.txt')