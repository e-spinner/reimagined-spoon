## Background Information
#### From the Client
"I am looking for a software alternative to automate the grading of weekly homework assignments. The requirements of this software are as follows: grading highly technical, math focused course work and written problems (like short answers). Have a graphical interface to input the pdf's to grade and output all the pdf's, graded, into a folder that can be uploaded to canvas. The answer key will be provided to the auto-grader. If the grade is of low confidence, the auto grader should inform the user for them to review."

#### Possible Users
- Professors how don't know how to use technology that well 
- Professors who are old
- Professors who have hundreds of students that they are grading 
- Professors who are on tight timelines 
#### what this means 
- needs to be easy to use 
- needs to be visually appealing (preference)
- Mostly used on windows devices but could be used on mac or Linux devices 
- must be reasonably fast
- must be as accurate as possible
- PDF will be the main document format

## Pipeline 

1. students will submit their homework on specific paper that will be used for grading
	1. This paper will have a predetermined box that students will write their answers
	2. This box will contain another box that the student must fill in to indicate that this is their answer to the question
	3. The question number will be written in a pre designated box Labeled answer
	4. The student will mark the bottom right corner box with an x to let the program know that this is the page to be graded
2. The professor will upload an answer key containing a numerical answer or keywords for the given assignment
	1. The answer key will also contain point breakdowns for each question as well as how many points the assignment is worth 
3. The professor will upload all the homework submissions from a folder
	1. The program should look for document types that are not supported and put them in a separate file for the professor to review later. 
4. The program will grade the homework 
	1. provide x's to parts that are wrong and check marks to parts that are right 
	2. these x's or check marks will be placed next to the answer
5. The program will print the correct number of points over the possible number of points next to the name of the student. it will also print the percentage
	1. the program will put the information into the thrid box on the top of the paper
6. The program will output the grades to a spreadsheet software of some kind
	1. output to excel if excel is detected 
	2. output to LibreOffice calc if calc is detected 
	3. prefer excel over LibreOffice
7. END

## some Requirements 
The app must be made into an executable and not require the command line at the end of the development. 

no paid API's are allowed because all of this must be run locally. 