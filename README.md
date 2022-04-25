# Course of Action Generator

The Course of Action (CoA) generator operates on a model of an IT architecture as used by the ADG and generates a set of defences that are inactive in the model and are suggested to activate. In SOCCRATES this is used to suggest defences improving the security of ICT infrastructure to the SOC analyst. The CoA generator forms a feedback loop with the ADG analyser. To drive the optimi-zation process, the generator computes a partial response to the threat based on the input attack path, run the ADG analyser to obtain the expected behaviour of the attacker under this partial re-sponse, repeat the procedure on the newly obtained attack path, etc. These iterations thus happen inside the CoA generator component without the involvement of the central orchestrator (OIE). High Level Architecture of CoA Generator is shown as follwos. CoA Cortex Analyser is written to integrate CoA generator to the OIE of SOCCRATES. Simulation id of an ADG analysis is required by CoA generator to start its computation, there are a few optional request parameters (costs, budgets, and inherent design restrictions).

<img src="https://user-images.githubusercontent.com/86651387/165049617-3f2d6438-2a81-422f-a1a6-6d79980221e8.png" width="600" height="300">

## CoA Deployment 

The CoA component is a multi-user web-based platform. The CoA deployment includes a virtual machine instance holding the CoA component and user databases. CoA services are accessed via a APIs. The CoA component can be executed directly on dedicated hardware or in a VM with a sup-ported guest OS and can be deployed on most modern servers, workstations or laptops.

## Requirements and Installation

The CoA component requires a machine (dedicated hardware or virtual) with at least 8GB RAM and 20GB of storage, and currently supports the following operating systems: Windows and Ubuntu Server 18.04/20.04. CoA component execution requires user credentials.

## Language Support

The CoA component is independent of what modelling language the ADG is using, as long as it is defined in the Meta Attack Language. However, defence step implementation costs needs to be defined separately per model (or language). In SOCCRATES we use the language named coreLang for which we have assigned some default costs for a subset of all defences in the language.

## Functional Specification

* Functions of CoA generator:

Input: 

1) Pointer to an attack defence graph model in the form of securiCAD simulation id. In this model one or more target attack steps are specified representing high value as-sets that are the ones that are to be protected. (To be provided by the ADG component.)
2) The information on cost of implementation of defences (potentially in multiple cost dimen-sions) and the available budget. (To be provided by the SOC analyst.) 

Output:

1) Initial Time-to-compromise values for each target attack step in the securiCAD model
2) A list of CoAs, each CoA includes the following information:

    *	Efficiency score of the defences as calculated by the CoA generator used for priori-tization inside the CoA generator algorithm
    *	Projected time-to-compromise values after implementing the defences in the course of action    
    *	Cost of implementation of CoA (in multiple cost dimensions)    
    *	Set of ordered defences in the securiCAD model from the ADG component
    *	Web Link to the simulation report in securiCAD after adding the CoA defences

## Integration 

The functionality provided by the CoA to the SOCCRATES platform is utilized via the CoA Cortex Analyser. The simulation id is a mandatory parameter required whereas all other parameters are optional. If budgets are not provided, then CoA generation will assume infinite budget. If costs are not provided zero costs will be assumed. If no design restrictions are provided none will be assumed.

## License

* Copyright © 2020-2021 [Mathias Ekstedt](mailto:mekstedt@kth.se)
* Copyright © 2020-2021 [Wojciech Wideł](mailto:widel@kth.se)
* Copyright © 2021 [Preetam Mukherjee](mailto:preetam@kth.se)
* Copyright © 2021 [Ashish Kumar Dwivedi](mailto:dwvedi@kth.se)
* Copyright © 2021 [Giuseppe Nebbione](mailto:nebbione@kth.se)

Licensed under the [Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0).
