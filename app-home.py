import numpy as np
import cv2
from flask import Flask, render_template,Response, request, send_file,redirect,flash,session,jsonify
from io import BytesIO
import pyautogui
import utilis
import os
import mysql.connector
from flask_sqlalchemy import SQLAlchemy
#############################
path="10.jpg"
widthImg = 500
heightImg = 500

#questions = 10
#choices = 5
#ans = [1,2,0,1,4,0,4,1,3,2]  #defining an answer list
#ans = [1,2,1,1,4]
global questions, choices, ans
webcamFeed = True
cameraNo = 0
############################

app = Flask(__name__, template_folder='templates') #initialize flask
app.secret_key=os.urandom(24)#for opening webpage on different tab users login login should not appear again instad it should save the cookies and it should be directl logged in


conn =mysql.connector.connect(host='localhost',username='root',password='',database='omr_logs' )
cursor=conn.cursor()



db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), nullable=False, unique=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)

# Initialize the webcam
cap= cv2.VideoCapture(cameraNo)
cap.set(10,150)
def gen_frames():
    while True:
        success, img = cap.read()
        if not success:
            break
        else:
            # PREPROCESSING
            img = cv2.resize(img, (widthImg, heightImg))
            imgContours = img.copy()
            imgFinal = img.copy()
            imgBiggestContours = img.copy()
            imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            imgBlur = cv2.GaussianBlur(imgGray, (5, 5), 1)
            imgCanny = cv2.Canny(imgBlur, 10, 50)

            try:
                # FINDING ALL THE CONTOURS
                contours, hierarchy = cv2.findContours(imgCanny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                cv2.drawContours(imgContours, contours, -1, (0, 255, 0), 10)

                # FIND RECTANGLES
                rectCon = utilis.rectCountour(contours)
                biggestContour = utilis.getCornerPoints(rectCon[0])
                gradePoints = utilis.getCornerPoints(rectCon[1])

                if biggestContour.size != 0 and gradePoints.size != 0:
                    cv2.drawContours(imgBiggestContours, biggestContour, -1, (0, 255, 0), 20)
                    cv2.drawContours(imgBiggestContours, gradePoints, -1, (255, 0, 0), 20)

                    biggestContour = utilis.reorder(biggestContour)
                    gradePoints = utilis.reorder(gradePoints)

                    pt1 = np.float32(biggestContour)
                    pt2 = np.float32([[0, 0], [widthImg, 0], [0, heightImg], [widthImg, heightImg]])
                    matrix = cv2.getPerspectiveTransform(pt1, pt2)
                    imgWarpColored = cv2.warpPerspective(img, matrix, (widthImg, heightImg))

                    ptG1 = np.float32(gradePoints)
                    ptG2 = np.float32([[0, 0], [325, 0], [0, 150], [325, 150]])
                    matrixG = cv2.getPerspectiveTransform(ptG1, ptG2)
                    imgGradeDisplay = cv2.warpPerspective(img, matrixG, (325, 150))
                    # cv2.imshow("Grade", imgGradeDisplay)

                    # APPLY THRESHOLD
                    imgWarpGray = cv2.cvtColor(imgWarpColored, cv2.COLOR_BGR2GRAY)
                    imgThresh = cv2.threshold(imgWarpGray, 140, 255, cv2.THRESH_BINARY_INV)[1]

                    boxes = utilis.splitBoxes(imgThresh, questions, choices)
                    # cv2.imshow("Test",boxes[1])
                    # print(cv2.countNonZero(boxes[1]),cv2.countNonZero(boxes[2]))

                    # GETTING NON-ZERO PIXEL VALUES OF EACH BOX
                    myPixelVal = np.zeros((questions, choices))
                    countC = 0
                    countR = 0

                    for image in boxes:
                        totalPixels = cv2.countNonZero(image)
                        myPixelVal[countR][countC] = totalPixels
                        countC += 1
                        if (countC == choices): countR += 1; countC = 0
                    # print(myPixelVal)

                    # FINDING INDEX VALUES OF THE MARKINGS
                    myIndex = []
                    for x in range(0, questions):
                        arr = myPixelVal[x]
                        # print("arr",arr)
                        myIndexVal = np.where(arr == np.amax(arr))
                        # print(myIndexVal[0])
                        myIndex.append(myIndexVal[0][0])
                    # print(myIndex)

                    # GRADING
                    grading = []
                    for x in range(0, questions):
                        if ans[x] == myIndex[x]:
                            grading.append(1)
                        else:
                            grading.append(0)
                    # print(grading)
                    score = (sum(grading) / questions) * 100  # FINAL GRADE
                    print(score)

                    # DISPLAYING ANSWERS
                    imgResult = imgWarpColored.copy()
                    imgResult = utilis.showAnswers(imgResult, myIndex, grading, ans, questions, choices)
                    imgRawDrawing = np.zeros_like(imgWarpColored)
                    imgRawDrawing = utilis.showAnswers(imgRawDrawing, myIndex, grading, ans, questions, choices)
                    invMatrix = cv2.getPerspectiveTransform(pt2, pt1)
                    imgInvWrap = cv2.warpPerspective(imgRawDrawing, invMatrix, (widthImg, heightImg))

                    imgRawGrade = np.zeros_like(imgGradeDisplay)
                    cv2.putText(imgRawGrade, str(int(score)) + "%", (60, 100), cv2.FONT_HERSHEY_COMPLEX, 3,
                                (0, 255, 255), 3)  # PERCENTAGE SHOW
                    invMatrixG = cv2.getPerspectiveTransform(ptG2, ptG1)
                    imgInvGradeDisplay = cv2.warpPerspective(imgRawGrade, invMatrixG, (widthImg, heightImg))

                    imgFinal = cv2.addWeighted(imgFinal, 1, imgInvWrap, 1, 0)
                    imgFinal = cv2.addWeighted(imgFinal, 1, imgInvGradeDisplay, 1, 0)

                imgBlank = np.zeros_like(img)
                imgArray = ([img, imgGray, imgBlur, imgCanny],
                            [imgContours, imgBiggestContours, imgWarpColored, imgThresh],
                            [imgResult, imgRawDrawing, imgInvWrap, imgFinal])
            except:
                imgBlank = np.zeros_like(img)
                imgArray = ([img, imgGray, imgBlur, imgCanny],
                            [imgBlank, imgBlank, imgBlank, imgBlank],
                            [imgBlank, imgBlank, imgBlank, imgBlank])

            lables = [['Original', "Gray", "Blur", "Canny"],
                      ["Contour", "BiggestContours", "Warp", "Threshold"],
                      ["Result", "RawDrawing", "InvWrap", "Final"]]

            imgStacked = utilis.stackImages(imgArray, 0.35, lables)

            if cv2.waitKey(1) & 0xFF == ord('s'):
                cv2.imwrite("FinalResult.jpg", imgFinal)
                cv2.waitKey(300)

            ret, buffer = cv2.imencode('.jpg', imgFinal)
            frame = buffer.tobytes()

            yield (b' --frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame
                   + b'\r\n\r\n')


@app.route('/')
def home():
        return render_template('home-final.html')

'''
@app.route('/login_validation', methods=['POST','GET'])
def login_validation():
    email=request.json.get('email')
    password=request.json.get('password')

    cursor.execute("""SELECT * from `users` WHERE `email` LIKE '{}' AND `password` LIKE '{}'"""
                   .format(email,password))

    users=cursor.fetchall()

    #if len(users)>0:
        #session['id']=users[0][0]#create cookie
        #session['logged_in'] = True
        #return redirect('/')
    #else:
        #return redirect('/')
    if len(users)>0:  # Replace this condition with your actual login logic
        session['id']=users[0][0]#create cookie
        session['login_successful'] = True
        if 'id' in session:
            return jsonify({"login_successful": True})
        else:
            return jsonify({"login_successful": False})
'''

@app.route('/login_validation', methods=['POST', 'GET'])
def login_validation():
    email = request.json.get('email')
    password = request.json.get('password')

    cursor.execute("""SELECT * from `users` WHERE `email` LIKE '{}' AND `password` LIKE '{}'"""
                   .format(email, password))

    users = cursor.fetchall()

    if len(users) > 0:
        session['id'] = users[0][0]  # Create a session
        session['login_successful'] = True
        return jsonify({"login_successful": True})
    else:
        return jsonify({"login_successful": False})


@app.route('/add_user', methods=['POST','GET'])
def add_user():
    username = request.json.get('username')
    email = request.json.get('email')
    password = request.json.get('password')

    cursor.execute("""INSERT into `users` (`id`,`username`,`email`,`password`) VALUES
    (NULL,'{}','{}','{}')""".format(username,email,password))
    conn.commit()
    cursor.execute("""SELECT * from `users` WHERE `email` LIKE '{}'""".format(email))
    my_user=cursor.fetchall()
    session['id']=my_user[0][0]
    if cursor.rowcount > 0:
            # User was added successfully
        response_data = {"signup_successful": True}
    else:
        # User was not added (an error occurred or no rows were affected)
        response_data = {"signup_successful": False}

        # Return a JSON response with the 'application/json' Content-Type
    return jsonify(response_data)
@app.route('/main')
def main():
    if 'id' in session:
        return render_template('index.html',data=[{'name':'5'}, {'name':'10'}])
    else :
        return redirect('/')


@app.route('/capture', methods=['POST'])
def capture():
    screenshot = pyautogui.screenshot()
    screenshot_bytes = BytesIO()
    screenshot.save(screenshot_bytes, format='PNG')
    screenshot_bytes.seek(0)

    return send_file(
        screenshot_bytes,
        as_attachment=True,
        download_name='screenshot.png',
        mimetype='image/png'
    )


@app.route('/video')
def video():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/data/', methods = ['POST','GET'])
def data():
    if 'id' in session:
        global questions, choices, ans
        if request.method == 'POST':
        # Get user input from the form
            questions = int(request.form.get('questions'))

            choices = int(request.form.get('choices'))

            ans_str = request.form.get('ans')

    # Convert the comma-separated string of answers to a list of integers
            ans = [int(x) for x in ans_str.split(',')]
    #return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
        return render_template('index.html')
    else:
        return redirect('/')

@app.route('/logout')
def logout():
    if 'id' in session:
        session.pop('id')
    return redirect('/')

@app.route('/profile')
def profile():
    cursor.execute("SELECT username, email FROM users WHERE id = 1")  # Adjust the query as needed
    omr_logs = cursor.fetchone()

    return render_template('profile.html', omr_logs=omr_logs)

@app.route('/aboutus')
def aboutus():
    return render_template('aboutus.html')

@app.route('/howtouse')
def howtouse():
    return render_template('howtouse.html')

if __name__ == '__main__':
    app.run(debug=True)
