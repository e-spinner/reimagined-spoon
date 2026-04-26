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

1. Students will submit a PDF containing examples of how they write letters, numbers, fractions, square roots, parenthesis, ect. so that an ai model can be optimized for their specific handwriting. 
	1. The AI must be at least 80% accurate on the students handwritten text. 
	2. students will write each symbol 100 times 
	3. an ensemble method AI is what will be preferred for this task
2. The professor will upload a LaTex rendered document which will act as the answer key 
	1. The answer key will also contain point breakdowns as well as how many points the assignment is worth 
3. The professor will upload all the homework submissions from a folder
	1. The program should look for document types that are not supported and put them in a separate file for the professor to review later. 
4. The program will grade the homework 
	1. provide x's to parts that are wrong and check marks to parts that are right 
5. The program will print the correct number of points over the possible number of points next to the name of the student. it will also print the percentage
6. The program will output the grades to a spreadsheet software of some kind
	1. output to excel if excel is detected 
	2. output to LibreOffice calc if calc is detected 
7. END

## some Requirements 
The app must be made into an executable and not require the command line at the end of the development. 

no paid API's are allowed because all of this must be run locally. 