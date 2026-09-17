# Memorability incremental-episodic task pilot (n=20, 10 for memorability and 10 for distinctiveness)

This data is from 2 versions of the incremental-episodic task, piloted with 10 participants each. 

Participants chose cards depicting objects from two decks (orange and blue) with distinct and reversing expected values. They could use these deck values to make their choice, or sometimes could instead choose based on the value of a card for an image they had seen before, retrieved from memory. 

The two manipulations were: 
1. "Memorability": images were selected from the [MEMCAT dataset](https://gestaltrevision.be/projects/memcat/) with pre-collected memorability data. The images with the top and bottom 100 memorability scores were sampled, such that each image was from a unique category (e.g., no two aardvarks). Half of the images on the cards were high-memorability, and half were low; we then can compute their episodic choice behavior for the high and low cards respectively when encountered again.
2. "Distinctiveness": half of the objects were unique objects, sampled randomly from the MEMCAT dataset. Half were airplanes, which looked very similar. This made it extremely difficult to use episodic memory to retrieve the value associated with a single airplane.

The data for these two pilots are shown in `ei-distinct-data.png` and `ei-mem-data.png`. The key plot is in the upper left, showing people's sensitivity to episodic object value in their choice behavior, comparing our two conditions. 

This task would be good to revisit with value-associability instead of image memorability! However, it makes more sense to eliminate the incremental element of the task, and replicate the episodic-only choice task from [Duncan and Shohamy 2016](http://duncanlab.org/wp-content/uploads/2018/04/Duncan_2016.pdf).