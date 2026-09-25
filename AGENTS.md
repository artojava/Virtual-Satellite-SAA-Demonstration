# Agent instructions

## Project overview

This project demostrates how Single Event Effects (SEE) occur in a satellite orbiting the Earth (Low Earth Orbit). It uses a mock satellite orbit, visualizing the orbit and the effects of radiation on the satellite's components by generating virtual errors on a hypothetical memory on board. The goal is to visualize the South Atlantic Anomaly (SAA) by plotting the position of the satellite over time and the locations of the errors that occur.

## Coding instructions

* The code should be written in Python and use libraries such as Matplotlib for plotting, NumPy for numerical operations, and any other necessary libraries for simulating the satellite's orbit and the effects of radiation.
* Project is maintained using `uv`
* The code should be modular, with clear separation of concerns between different components (e.g., orbit simulation, error generation, plotting).
* The visualization should include a 2D plot of the satellite's orbit around the Earth, with markers indicating where errors occur due to radiation effects.
* The simulation should account for the satellite's position over time, and the errors should be generated based on the satellite's location relative to the South Atlantic Anomaly.
* The code should include comments and documentation to explain the logic and functionality of each component.
* The GUI should be a simple web interface that allows users to start the simulation, view the orbit and error locations, and adjust parameters such as the satellite's speed and altitude.
* The GUI should indicate the number of errors generated and their locations on the orbit plot.

## Additional requirements

* The project should include a README file with instructions on how to set up and run the simulation, as well as any dependencies that need to be installed.
* The project should include unit tests to verify the correctness of the orbit simulation and error generation logic.
* The project should be structured in a way that allows for easy extension and modification, such as adding new features or improving the visualization.
* The project should be designed with performance in mind, ensuring that the simulation runs efficiently even for longer durations or higher resolutions of the orbit plot.