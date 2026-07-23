# FACTS Overview

This page contains a plain-language overview of the Framework for Assessing Changes to Sea-level (FACTS) and elements of FACTS experiments as well as answers to common questions related to FACTS. It is meant to accompany the technical documentation about FACTS2 software and the FACTS-experiment-builder (FEB) in this repository. For a comprehensive scientific description of the Framework for Assessing Changes to Sea-level (FACTS), please refer to [Kopp et al., 2023](https://gmd.copernicus.org/articles/16/7461/2023/). 

If you are new to FACTS and/or FACTS2, please checkout our [glossary](./FACTS_GLOSSARY.md) to familiarize yourself with important terms. 

## Separating vertical land motion processes in FACTS experiments

FACTS modules represent different physical processes that contribute to global mean sea level (GMSL) and relative sea level (RSL) change. A FACTS experiment involves combining multiple modules in a coherent probabilistic framework. However, due to the highly spatially and temporally-variable nature of many vertical land motion processes that impact sea-level, researchers may prefer to evaluate these effects separately from other modules. 

To accommodate this separation, we suggest the following approach:

- Configure and run a FACTS experiment excluding vertical land motion modules (e.g. do not include the VLM modules in sealevel-step of feb setup-experiment),
- Run vertical land motion modules separately/offline (see individual modules for instructions),
- Combine results as appropriate/needed by running the [facts-total](https://github.com/fact-sealevel/facts-total) module directly, outside of FEB.

Evaluating vertical land motion processes separately from other sea-level modules in an experiment is not explicitly supported as of version 0.5.0 of the FACTS-experiment-builder (FEB), but is planned for a future release.
