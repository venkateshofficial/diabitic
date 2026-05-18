import socket
import time
import os
import requests
import json
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.factory import Factory
from kivy.properties import StringProperty, ObjectProperty, ListProperty
from kivy.metrics import dp
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.storage.jsonstore import JsonStore
from kivy.resources import resource_find

# Fix for source code inspection and absolute paths
__file__ = os.path.abspath('main.py')
BASE_DIR = os.path.dirname(__file__)

# ---------------------------------------------------------
# 1. FIREBASE AUTH LOGIC
# ---------------------------------------------------------
class FirebaseManager:
    def __init__(self):
        # API Key from your provided google-services.json
        self.api_key = "AIzaSyAkuoY69ivwbWyWHv7i2CegesjQmsZEW-s"
        self.signup_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={self.api_key}"
        self.signin_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={self.api_key}"

    def register(self, email, password):
        try:
            payload = {"email": email, "password": password, "returnSecureToken": True}
            response = requests.post(self.signup_url, data=json.dumps(payload), timeout=10)
            return response.ok, response.json()
        except Exception as e:
            return False, {"error": {"message": str(e)}}

    def login(self, email, password):
        try:
            payload = {"email": email, "password": password, "returnSecureToken": True}
            response = requests.post(self.signin_url, data=json.dumps(payload), timeout=10)
            return response.ok, response.json()
        except Exception as e:
            return False, {"error": {"message": str(e)}}

# ---------------------------------------------------------
# 2. HELPER CLASSES & LOGIC
# ---------------------------------------------------------
class Gradient:
    @staticmethod
    def horizontal(r1, g1, b1, a1, r2, g2, b2, a2):
        texture = Texture.create(size=(2, 1), colorfmt='rgba')
        p1 = [int(c * 255) for c in (r1, g1, b1, a1)]
        p2 = [int(c * 255) for c in (r2, g2, b2, a2)]
        buf = bytes(p1 + p2)
        texture.blit_buffer(buf, colorfmt='rgba', bufferfmt='ubyte')
        return texture

def is_connected():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=2)
        return True
    except OSError:
        return False

# ---------------------------------------------------------
# 3. KV DESIGN
# ---------------------------------------------------------
Builder.load_string('''
<FieldLabel@Label>:
    font_size: '14sp'
    halign: 'left'
    valign: 'middle'
    text_size: self.size
    color: 0.4, 0.4, 0.4, 1
    size_hint_y: None
    height: dp(18)
    bold: True

<FormInput@TextInput>:
    multiline: False
    padding: [dp(15), dp(12)]
    cursor_color: 0.2, 0.2, 0.2, 1
    font_size: '16sp'
    background_active: ''
    background_normal: ''
    background_color: 0, 0, 0, 0
    foreground_color: 0.1, 0.1, 0.1, 1
    canvas.before:
        Color:
            rgba: 254/255, 243/255, 230/255, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(8),]
        Color:
            rgba: (93/255, 184/255, 219/255, 1) if self.focus else (0,0,0,0)
        Line:
            width: dp(1.1)
            rounded_rectangle: (self.x, self.y, self.width, self.height, dp(8))

<VectorCloudError>:
    canvas:
        Color:
            rgba: self.error_color
        Ellipse:
            pos: (self.center_x - dp(25), self.center_y - dp(28))
            size: (dp(50), dp(50))
        Color:
            rgba: (1, 1, 1, 1)
        Rectangle:
            pos: (self.center_x - dp(3), self.center_y - dp(8))
            size: (dp(6), dp(18))
        Ellipse:
            pos: (self.center_x - dp(3), self.center_y - dp(20))
            size: (dp(6), dp(6))
        Color:
            rgba: (1, 1, 1, 1)
        Line:
            bezier: (self.center_x - dp(50), self.center_y - dp(10), self.center_x - dp(70), self.center_y + dp(10), self.center_x - dp(40), self.center_y + dp(40), self.center_x - dp(20), self.center_y + dp(25))
            width: dp(1.5)
        Line:
            bezier: (self.center_x - dp(20), self.center_y + dp(25), self.center_x, self.center_y + dp(55), self.center_x + dp(30), self.center_y + dp(45), self.center_x + dp(45), self.center_y + dp(20))
            width: dp(1.5)
        Line:
            bezier: (self.center_x + dp(45), self.center_y + dp(20), self.center_x + dp(65), self.center_y + dp(5), self.center_x + dp(60), self.center_y - dp(10), self.center_x + dp(40), self.center_y - dp(10))
            width: dp(1.5)
        Line:
            points: [self.center_x - dp(50), self.center_y - dp(10), self.center_x + dp(40), self.center_y - dp(10)]
            width: dp(1.5)

<NetworkErrorScreen>:
    canvas.before:
        Color:
            rgba: (35/255, 16/255, 47/255, 1)
        Rectangle:
            pos: self.pos
            size: self.size
    BoxLayout:
        orientation: 'vertical'
        size_hint: (0.85, 0.45)
        pos_hint: {'center_x': 0.5, 'center_y': 0.5}
        padding: [dp(20), dp(40), dp(20), dp(40)]
        spacing: dp(30)
        canvas.before:
            Color:
                rgba: (1, 1, 1, 1)
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [dp(40),]
        VectorCloudError:
            size_hint_y: 0.6
        Label:
            text: "Please Check Your Network\\nConnections"
            color: (0.2, 0.2, 0.3, 1)
            font_size: '18sp'
            halign: 'center'
            valign: 'middle'
            size_hint_y: 0.4

<SplashScreen>:
    canvas.before:
        Color:
            rgba: (35/255, 16/255, 47/255, 1)
        Rectangle:
            pos: self.pos
            size: self.size
    FloatLayout:
        Widget:
            size_hint: None, None
            size: 280, 280
            pos_hint: {'center_x': 0.5, 'center_y': 0.5}
            canvas:
                Color:
                    rgba: 1, 1, 1, 1
                Ellipse:
                    pos: self.pos
                    size: self.size
                Color:
                    rgba: 0.8, 0.1, 0.1, 1
                Ellipse:
                    pos: self.x + 70, self.y + 45
                    size: 140, 140
                Triangle:
                    points: [self.x+70, self.y+115, self.x+210, self.y+115, self.x+140, self.y+230]
                Color:
                    rgba: 1, 1, 1, 1
                Rectangle:
                    pos: self.x + 122, self.y + 105
                    size: 36, 10
                Rectangle:
                    pos: self.x + 135, self.y + 92
                    size: 10, 36

<LoginScreen>:
    user_input: user_input
    pass_input: pass_input
    canvas.before:
        Color:
            rgba: (35/255, 16/255, 47/255, 1)
        Rectangle:
            pos: self.pos
            size: self.size
    AnchorLayout:
        BoxLayout:
            orientation: 'vertical'
            size_hint: None, None
            size: "320dp", "450dp"
            padding: "30dp"
            spacing: "20dp"
            canvas.before:
                Color:
                    rgba: (0.4, 0.2, 0.8, 1)
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [35,]
            Label:
                text: "Sign In"
                font_size: "32sp"
                bold: True
            TextInput:
                id: user_input
                hint_text: "Email ID"
                multiline: False
                size_hint_y: None
                height: "50dp"
                background_color: 0,0,0,0
                foreground_color: 1,1,1,1
                padding: [15, 15]
                canvas.before:
                    Color:
                        rgba: 1,1,1,0.2
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [25,]
            TextInput:
                id: pass_input
                hint_text: "Password"
                password: True
                multiline: False
                size_hint_y: None
                height: "50dp"
                background_color: 0,0,0,0
                foreground_color: 1,1,1,1
                padding: [15, 15]
                canvas.before:
                    Color:
                        rgba: 1,1,1,0.2
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [25,]
            Button:
                text: "LOGIN"
                size_hint_y: None
                height: "55dp"
                color: (0.3, 0.1, 0.6, 1)
                background_color: 0,0,0,0
                on_release: root.verify_credentials()
                canvas.before:
                    Color:
                        rgba: 1,1,1,1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [27.5,]
            Button:
                text: "New here? Create Account"
                size_hint_y: None
                height: "30dp"
                background_color: 0,0,0,0
                font_size: "14sp"
                on_release: root.manager.current = 'register'

<RegisterScreen>:
    reg_user: reg_user
    reg_pass: reg_pass
    reg_gmail: reg_gmail
    reg_mobile: reg_mobile
    canvas.before:
        Color:
            rgba: (35/255, 16/255, 47/255, 1)
        Rectangle:
            pos: self.pos
            size: self.size
    AnchorLayout:
        BoxLayout:
            orientation: 'vertical'
            size_hint: None, None
            size: "320dp", "580dp"
            padding: [dp(25), dp(30), dp(25), dp(30)]
            spacing: dp(8)
            canvas.before:
                Color:
                    rgba: 245/255, 245/255, 250/255, 1
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [dp(35),]
            Label:
                text: "Create Account"
                font_size: '22sp'
                bold: True
                color: 93/255, 184/255, 219/255, 1
                size_hint_y: None
                height: dp(50)

            FieldLabel: 
                text: "Username"
            FormInput:
                id: reg_user
                size_hint_y: None
                height: dp(42)

            FieldLabel: 
                text: "Password"
            FormInput:
                id: reg_pass
                password: True
                size_hint_y: None
                height: dp(42)

            FieldLabel: 
                text: "Gmail Id"
            FormInput:
                id: reg_gmail
                size_hint_y: None
                height: dp(42)

            FieldLabel: 
                text: "Mobile No"
            FormInput:
                id: reg_mobile
                input_filter: 'int'
                size_hint_y: None
                height: dp(42)

            AnchorLayout:
                size_hint_y: None
                height: dp(70)
                Button:
                    text: "Create Account"
                    font_size: '18sp'
                    bold: True
                    size_hint: (0.9, None)
                    height: dp(50)
                    background_color: 0,0,0,0
                    on_release: root.validate_registration()
                    canvas.before:
                        Color:
                            rgba: (93/255, 184/255, 219/255, 1)
                        RoundedRectangle:
                            pos: self.pos
                            size: self.size
                            radius: [dp(12),]
            Button:
                text: "Already have an account? Sign In"
                size_hint_y: None
                height: dp(40)
                background_color: 0,0,0,0
                font_size: '14sp'
                color: 232/255, 108/255, 140/255, 1
                on_release: root.manager.current = 'login'

<EmptyFieldErrorScreen>:
    canvas.before:
        Color:
            rgba: (35/255, 16/255, 47/255, 1)
        Rectangle:
            pos: self.pos
            size: self.size
    AnchorLayout:
        BoxLayout:
            orientation: 'vertical'
            size_hint: None, None
            size: "320dp", "400dp"
            padding: "30dp"
            spacing: "10dp"
            canvas.before:
                Color:
                    rgba: 1, 1, 1, 1
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [40,]
            AnchorLayout:
                anchor_x: 'center'
                anchor_y: 'center'
                size_hint_y: 0.6
                Widget:
                    size_hint: None, None
                    size: "160dp", "160dp"
                    canvas:
                        Color:
                            rgba: 0.94, 0.94, 0.94, 1
                        Ellipse:
                            pos: self.pos
                            size: self.size
                        Color:
                            rgba: 1, 0, 0, 1
                        Line:
                            points: [self.center_x, self.center_y + 45, self.center_x, self.center_y + 5]
                            width: 12
                            cap: 'round'
                        Ellipse:
                            pos: self.center_x - 10, self.center_y - 30
                            size: 20, 20
            Label:
                id: error_label
                text: "!!! Please Enter All Fields Correctly"
                font_size: '16sp'
                color: 0.9, 0.3, 0.3, 1
                halign: 'center'
                text_size: self.width, None
                size_hint_y: 0.4

<AccountCreatedScreen>:
    canvas.before:
        Color:
            rgba: 0.1, 0, 0.15, 1
        Rectangle:
            pos: self.pos
            size: self.size
    AnchorLayout:
        BoxLayout:
            orientation: 'vertical'
            size_hint: None, None
            size: "300dp", "400dp"
            padding: "20dp"
            spacing: "15dp"
            canvas.before:
                Color:
                    rgba: 1, 1, 1, 1
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [40,]
            AnchorLayout:
                anchor_x: 'center'
                anchor_y: 'center'
                size_hint_y: 0.4
                Widget:
                    size_hint: None, None
                    size: "100dp", "100dp"
                    canvas:
                        Color:
                            rgba: 0.13, 0.75, 0.13, 1
                        Ellipse:
                            pos: self.pos
                            size: self.size
                        Color:
                            rgba: 1, 1, 1, 1
                        Line:
                            points: [self.center_x - 20, self.center_y, self.center_x - 5, self.center_y - 15, self.center_x + 25, self.center_y + 15]
                            width: 4
                            cap: 'round'
                            joint: 'round'
            Label:
                text: "Account Created\\nSuccessfully"
                font_size: '22sp'
                halign: 'center'
                color: 0.3, 0.3, 0.7, 1
                bold: True
                size_hint_y: 0.3
            Label:
                text: "Go to login your Account"
                font_size: '14sp'
                color: 0.8, 0.3, 0.2, 1
                size_hint_y: 0.1
            AnchorLayout:
                anchor_x: 'center'
                size_hint_y: 0.2
                Button:
                    text: "Sign In"
                    size_hint: None, None
                    size: "140dp", "48dp"
                    background_color: 0,0,0,0
                    on_release: root.manager.current = 'login'
                    canvas.before:
                        Color:
                            rgba: 0.5, 0, 0.8, 1
                        RoundedRectangle:
                            pos: self.pos
                            size: self.size
                            radius: [24,]

<SuccessScreen>:
    canvas.before:
        Color:
            rgba: (35/255, 16/255, 47/255, 1)
        Rectangle:
            pos: self.pos
            size: self.size
    FloatLayout:
        Widget:
            size_hint: None, None
            size: "120dp", "120dp"
            pos_hint: {'center_x': 0.5, 'center_y': 0.6}
            canvas:
                Color:
                    rgba: (46/255, 204/255, 113/255, 1)
                Ellipse:
                    pos: self.pos
                    size: self.size
                Color:
                    rgba: (1, 1, 1, 1)
                Line:
                    points: [self.x + self.width*0.3, self.y + self.height*0.5, self.x + self.width*0.45, self.y + self.height*0.35, self.x + self.width*0.7, self.y + self.height*0.65]
                    width: 3
                    cap: 'round'
                    joint: 'round'
        Label:
            text: "Signed in Successfully"
            font_size: "20sp"
            color: (0.8, 0.4, 0.6, 1)
            pos_hint: {'center_x': 0.5, 'center_y': 0.4}

<ErrorScreen>:
    canvas.before:
        Color:
            rgba: (35/255, 16/255, 47/255, 1)
        Rectangle:
            pos: self.pos
            size: self.size
    FloatLayout:
        Widget:
            size_hint: None, None
            size: "120dp", "120dp"
            pos_hint: {'center_x': 0.5, 'center_y': 0.6}
            canvas:
                Color:
                    rgba: (0.9, 0.2, 0.2, 1)
                Ellipse:
                    pos: self.pos
                    size: self.size
                Color:
                    rgba: (1, 1, 1, 1)
                Line:
                    points: [self.x + self.width*0.35, self.y + self.height*0.35, self.x + self.width*0.65, self.y + self.height*0.65]
                    width: 3
                    cap: 'round'
                Line:
                    points: [self.x + self.width*0.35, self.y + self.height*0.65, self.x + self.width*0.65, self.y + self.height*0.35]
                    width: 3
                    cap: 'round'
        Label:
            id: error_label
            text: "Username and Password\\nare Incorrect"
            font_size: "18sp"
            halign: 'center'
            color: (1, 1, 1, 1)
            pos_hint: {'center_x': 0.5, 'center_y': 0.45}
        Button:
            text: "Go Back"
            size_hint: None, None
            size: "180dp", "50dp"
            pos_hint: {'center_x': 0.5, 'center_y': 0.3}
            background_color: 0,0,0,0
            on_release: root.manager.current = 'login'
            canvas.before:
                Color:
                    rgba: (0.1, 0.1, 0.1, 1)
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [25,]

<PredictionResultScreen>:
    prediction_text: ""
    canvas.before:
        Color:
            rgba: (35/255, 16/255, 47/255, 1)
        Rectangle:
            pos: self.pos
            size: self.size
    AnchorLayout:
        BoxLayout:
            orientation: 'vertical'
            size_hint: None, None
            size: "320dp", "350dp"
            padding: "30dp"
            spacing: "20dp"
            canvas.before:
                Color:
                    rgba: (0.95, 0.96, 0.98, 1)
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [35,]
            Label:
                text: "Prediction Result"
                font_size: "28sp"
                bold: True
                color: (0.2, 0.2, 0.2, 1)
                size_hint_y: None
                height: dp(60)
            Label:
                text: root.prediction_text
                font_size: "22sp"
                halign: 'center'
                valign: 'middle'
                text_size: self.width, None
                color: (0.3, 0.1, 0.6, 1)
                size_hint_y: 0.6
            Button:
                text: "Back to Home"
                size_hint_y: None
                height: "55dp"
                background_color: 0,0,0,0
                on_release: root.manager.current = 'main_list'
                canvas.before:
                    Color:
                        rgba: (93/255, 184/255, 219/255, 1)
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [27.5,]

<PlaceholderBox>:
    size_hint_y: None
    height: "50dp"
    canvas.before:
        Color:
            rgba: 1, 1, 1, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [25,]
            texture: app.get_gradient()
    TextInput:
        id: text_input_field
        hint_text: root.text_val
        hint_text_color: 0.9, 0.9, 0.9, 0.7
        multiline: False
        background_color: 0, 0, 0, 0
        foreground_color: 1, 1, 1, 1
        padding: ["15dp", "12dp"]
        input_filter: root.input_filter
        on_text: root.input_text = self.text

<MainListScreen>:
    input_pregnancies: input_pregnancies
    input_glucose: input_glucose
    input_bloodpressure: input_bloodpressure
    input_skinthickness: input_skinthickness
    input_insulin: input_insulin
    input_bmi: input_bmi
    input_diabetespedigree: input_diabetespedigree
    input_age: input_age
    canvas.before:
        Color:
            rgba: (35/255, 16/255, 47/255, 1)
        Rectangle:
            pos: self.pos
            size: self.size
    AnchorLayout:
        BoxLayout:
            orientation: 'vertical'
            size_hint: 0.9, 0.9
            padding: ["20dp", "15dp", "20dp", "25dp"]
            spacing: "15dp"
            canvas.before:
                Color:
                    rgba: 0.95, 0.96, 0.98, 1
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [40,]
            Label:
                text: "Diabetes Prediction"
                font_size: "22sp"
                bold: True
                color: 0.2, 0.2, 0.2, 1
                size_hint_y: None
                height: dp(50)
            ScrollView:
                GridLayout:
                    cols: 1
                    size_hint_y: None
                    height: self.minimum_height
                    padding: ["5dp", "5dp"]
                    spacing: "12dp"
                    PlaceholderBox:
                        id: input_pregnancies
                        text_val: "Pregnancies"
                        input_filter: 'int'
                    PlaceholderBox:
                        id: input_glucose
                        text_val: "Glucose"
                        input_filter: 'float'
                    PlaceholderBox:
                        id: input_bloodpressure
                        text_val: "Blood Pressure"
                        input_filter: 'float'
                    PlaceholderBox:
                        id: input_skinthickness
                        text_val: "Skin Thickness"
                        input_filter: 'float'
                    PlaceholderBox:
                        id: input_insulin
                        text_val: "Insulin"
                        input_filter: 'float'
                    PlaceholderBox:
                        id: input_bmi
                        text_val: "BMI"
                        input_filter: 'float'
                    PlaceholderBox:
                        id: input_diabetespedigree
                        text_val: "Diabetes Pedigree Function"
                        input_filter: 'float'
                    PlaceholderBox:
                        id: input_age
                        text_val: "Age"
                        input_filter: 'int'
            Button:
                text: "Predict"
                size_hint: None, None
                size: "200dp", "55dp"
                pos_hint: {'center_x': 0.5}
                font_size: "20sp"
                bold: True
                color: (0.8, 0.4, 0.5, 1)
                background_color: 0,0,0,0
                on_release: root.make_prediction()
                canvas.before:
                    Color:
                        rgba: (34/255, 34/255, 34/255, 1)
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [20,]
''')

# ---------------------------------------------------------
# 4. PYTHON LOGIC
# ---------------------------------------------------------
class VectorCloudError(Widget):
    error_color = ListProperty([0.9, 0.2, 0.2, 1])

class NetworkErrorScreen(Screen):
    pass

class SplashScreen(Screen):
    def on_enter(self, *args):
        Clock.schedule_once(self.switch_to_login, 14)
    def switch_to_login(self, dt):
        app = App.get_running_app()
        self.manager.current = app.last_screen

class LoginScreen(Screen):
    user_input = ObjectProperty(None)
    pass_input = ObjectProperty(None)

    def verify_credentials(self):
        app = App.get_running_app()
        email = self.user_input.text.strip()
        password = self.pass_input.text.strip()

        if not email or not password:
            app.last_screen = 'login'
            self.manager.get_screen('empty_field_error').ids.error_label.text = "!!! Please Enter Email and Password!"
            self.manager.current = 'empty_field_error'
            return

        # Firebase Auth
        success, info = app.firebase.login(email, password)
        if success:
            app.save_login_session()
            self.manager.current = 'success'
        else:
            error_msg = info.get('error', {}).get('message', 'INVALID_CREDENTIALS')
            self.manager.get_screen('error').ids.error_label.text = f"Login Failed:\\n{error_msg.replace('_', ' ')}"
            self.manager.current = 'error'

class EmptyFieldErrorScreen(Screen):
    def on_enter(self, *args):
        Clock.schedule_once(self.back_to_previous, 2)
    def back_to_previous(self, dt):
        app = App.get_running_app()
        self.manager.current = app.last_screen

class AccountCreatedScreen(Screen):
    pass

class RegisterScreen(Screen):
    reg_user = ObjectProperty(None)
    reg_pass = ObjectProperty(None)
    reg_gmail = ObjectProperty(None)
    reg_mobile = ObjectProperty(None)

    def validate_registration(self):
        app = App.get_running_app()
        email = self.reg_gmail.text.strip()
        password = self.reg_pass.text.strip()

        if not all([self.reg_user.text.strip(), password, email, self.reg_mobile.text.strip()]):
            app.last_screen = 'register'
            self.manager.get_screen('empty_field_error').ids.error_label.text = "!!! Please Fill All Registration Fields!"
            self.manager.current = 'empty_field_error'
            return

        # Firebase Auth Registration
        success, info = app.firebase.register(email, password)
        if success:
            self.manager.current = 'account_success'
        else:
            error_msg = info.get('error', {}).get('message', 'REGISTRATION_FAILED')
            app.last_screen = 'register'
            self.manager.get_screen('empty_field_error').ids.error_label.text = f"Error: {error_msg.replace('_', ' ')}"
            self.manager.current = 'empty_field_error'

class SuccessScreen(Screen):
    def on_enter(self, *args):
        Clock.schedule_once(self.go_to_main, 2)
    def go_to_main(self, dt):
        self.manager.current = 'main_list'

class ErrorScreen(Screen):
    pass

class PredictionResultScreen(Screen):
    prediction_text = StringProperty("")

class PlaceholderBox(BoxLayout):
    text_val = StringProperty("Default")
    input_text = StringProperty("")
    input_filter = StringProperty(None, allownone=True)

class MainListScreen(Screen):
    input_pregnancies = ObjectProperty(None)
    input_glucose = ObjectProperty(None)
    input_bloodpressure = ObjectProperty(None)
    input_skinthickness = ObjectProperty(None)
    input_insulin = ObjectProperty(None)
    input_bmi = ObjectProperty(None)
    input_diabetespedigree = ObjectProperty(None)
    input_age = ObjectProperty(None)

    def make_prediction(self):
        app = App.get_running_app()
        fields = [
            self.input_pregnancies, self.input_glucose, self.input_bloodpressure,
            self.input_skinthickness, self.input_insulin, self.input_bmi,
            self.input_diabetespedigree, self.input_age
        ]

        try:
            if any(not f.input_text.strip() for f in fields):
                app.last_screen = 'main_list'
                self.manager.get_screen('empty_field_error').ids.error_label.text = "All fields are required!"
                self.manager.current = 'empty_field_error'
                return

            # Extract values
            data = [float(f.input_text.strip()) for f in fields]
            glucose = data[1]
            bmi = data[5]
            age = data[7]
            
            # Simple medical rule-based logic (Approximation)
            # High Glucose (>140) or High BMI (>30) or Age > 45 with some risk factors
            score = 0
            if glucose > 140: score += 2
            if glucose > 180: score += 3
            if bmi > 30: score += 1
            if bmi > 35: score += 2
            if age > 45: score += 1
            
            if score >= 3:
                result = "Positive (High Risk)"
            else:
                result = "Negative (Low Risk)"
                
            self.manager.get_screen('prediction_result').prediction_text = result
            self.manager.current = 'prediction_result'

        except Exception as e:
            app.last_screen = 'main_list'
            self.manager.get_screen('empty_field_error').ids.error_label.text = "Invalid Numeric Data!"
            self.manager.current = 'empty_field_error'

class VSKApp(App):
    last_screen = StringProperty('login')
    firebase = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.store = JsonStore('vsk_session.json')
        self.firebase = FirebaseManager()

    def get_gradient(self):
        return Gradient.horizontal(0.1, 0.4, 0.9, 1, 0.6, 0.2, 0.8, 1)

    def build(self):
        self.sm = ScreenManager(transition=NoTransition())
        self.sm.add_widget(SplashScreen(name='splash'))
        self.sm.add_widget(NetworkErrorScreen(name='network_error'))
        self.sm.add_widget(LoginScreen(name='login'))
        self.sm.add_widget(RegisterScreen(name='register'))
        self.sm.add_widget(AccountCreatedScreen(name='account_success'))
        self.sm.add_widget(EmptyFieldErrorScreen(name='empty_field_error'))
        self.sm.add_widget(ErrorScreen(name='error'))
        self.sm.add_widget(SuccessScreen(name='success'))
        self.sm.add_widget(MainListScreen(name='main_list'))
        self.sm.add_widget(PredictionResultScreen(name='prediction_result'))

        self.sm.bind(current=self.track_current_page)
        Clock.schedule_interval(self.check_global_network, 3)
        return self.sm

    def on_start(self):
        if self.store.exists('session'):
            data = self.store.get('session')
            if (time.time() - data['time']) < 2600:
                self.last_screen = data['page']
        else:
            self.last_screen = 'login'

    def save_login_session(self):
        self.store.put('session', time=time.time(), page='main_list')

    def track_current_page(self, instance, value):
        excluded = ['splash', 'network_error', 'empty_field_error', 'error', 'prediction_result']
        if value not in excluded:
            self.last_screen = value
            if self.store.exists('session'):
                t = self.store.get('session')['time']
                self.store.put('session', time=t, page=value)

    def check_global_network(self, dt):
        connected = is_connected()
        if not connected and self.sm.current != 'network_error':
            if self.sm.current != 'splash': self.last_screen = self.sm.current
            self.sm.current = 'network_error'
        elif connected and self.sm.current == 'network_error':
            self.sm.current = self.last_screen
            
if __name__ == '__main__':
    VSKApp().run()
