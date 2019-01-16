from flask import Flask, jsonify, request
app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello World!"


@app.route("/loc", methods=['POST'])
def loc():
    print(request.data)
    d = {}
    d['latitude'] = 40.741512
    d['longitude'] =  -73.647309

    return jsonify(d)

@app.route("/data", methods=['POST'])
def getData():
    print(request.data)

    return "Ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0",port=5000)
