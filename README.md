# Geniz

Geniz is an interactive code-gen app that explores a fundamentally different approach to coding tasks. Instead of manually writing code, users can leverage the power of large language models (LLMs) to generate solutions by simply providing the desired input and output.

Here is a demo video.
[![Demo Video](static/demo_1.gif)](https://www.youtube.com/watch?v=S_vB7qQ3qs4)

### Revolutionizing Coding

Geniz aims to change the way people tackle coding challenges from platforms like LeetCode, TopCoder, and USACO. Rather than spending hours coding and debugging, users can focus on defining the problem's requirements and let the LLMs handle the implementation details.

### Harnessing Local Code-Gen LLMs

Geniz represents the first practical application of local/smaller LLMs, enabling them to solve complex coding problems effectively. By running the LLMs locally, Geniz ensures privacy and allows users to benefit from the latest advancements in language models without relying on external services.


## Getting Started

To get started with Geniz, follow these steps:

* Clone the repository `git clone https://github.com/sudocode-ai/geniz.git`
* Install the dependencies: `cd geniz && pip install -e .`
* (Optional) Prepare keys.json (See keys.json.example), or type in the UI.
* Run the webapp: cd src/geniz/example && python webserver.py



## Benchmark

We’ve benchmarked a few different open source models against HumanEval **without** human interventions.

| Model                           | Baseline | Geniz (without human) |
| ------------------------------- | -------- | --------------------- |
| OpenCodeInterpreter-1.3B        | 48.7%*   | 72.0% (+45%)          |
| Llama-3-70b-instruct            | 81.7%    | 85.9% (+5%)           |
| Phi-3-mini-128k-instruct (3.8B) | 57.9%    | 74.1% (+28%)          |

Note: * is our reproduction.


## Contributing

We welcome contributions from the community! If you'd like to contribute to Geniz, please follow our contributing guidelines.
Contact person: [Ning Ren](https://www.linkedin.com/in/renning22/), [Alex Ngai](https://www.linkedin.com/in/alexngai/) and [Randy Song](https://www.linkedin.com/in/randy-song/).

## License

Geniz is released under the MIT License.
