import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  runApp(const VSKApp());
}

// ---------------------------------------------------------
// 1. FIREBASE AUTH LOGIC
// ---------------------------------------------------------
class FirebaseManager {
  final String apiKey = "AIzaSyAkuoY69ivwbWyWHv7i2CegesjQmsZEW-s";

  late final String signupUrl;
  late final String signinUrl;

  FirebaseManager() {
    signupUrl =
        "https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=$apiKey";
    signinUrl =
        "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=$apiKey";
  }

  Future<Map<String, dynamic>> register(String email, String password) async {
    try {
      final response = await http
          .post(
            Uri.parse(signupUrl),
            body: jsonEncode({
              "email": email,
              "password": password,
              "returnSecureToken": true,
            }),
            headers: {"Content-Type": "application/json"},
          )
          .timeout(const Duration(seconds: 10));

      return {
        "success": response.statusCode == 200,
        "data": jsonDecode(response.body),
      };
    } catch (e) {
      return {
        "success": false,
        "data": {
          "error": {"message": e.toString()},
        },
      };
    }
  }

  Future<Map<String, dynamic>> login(String email, String password) async {
    try {
      final response = await http
          .post(
            Uri.parse(signinUrl),
            body: jsonEncode({
              "email": email,
              "password": password,
              "returnSecureToken": true,
            }),
            headers: {"Content-Type": "application/json"},
          )
          .timeout(const Duration(seconds: 10));

      return {
        "success": response.statusCode == 200,
        "data": jsonDecode(response.body),
      };
    } catch (e) {
      return {
        "success": false,
        "data": {
          "error": {"message": e.toString()},
        },
      };
    }
  }
}

// Global helper to simulate network checks natively
Future<bool> isConnected() async {
  try {
    final result = await InternetAddress.lookup('google.com');
    return result.isNotEmpty && result[0].rawAddress.isNotEmpty;
  } on SocketException catch (_) {
    return false;
  }
}

// ---------------------------------------------------------
// 2. MAIN APPLICATION LAYER
// ---------------------------------------------------------
class VSKApp extends StatelessWidget {
  const VSKApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Diabetes Prediction App',
      theme: ThemeData(
        scaffoldBackgroundColor: const Color(0xff23102f),
        primaryColor: const Color(0xff5db8db),
      ),
      debugShowCheckedModeBanner: false,
      home: const RootHandler(),
    );
  }
}

class RootHandler extends StatefulWidget {
  const RootHandler({super.key});

  @override
  State<RootHandler> createState() => _RootHandlerState();
}

class _RootHandlerState extends State<RootHandler> {
  final FirebaseManager firebase = FirebaseManager();
  String currentScreen = 'splash';
  String lastScreen = 'login';
  Timer? networkTimer;
  bool isNetworkErrorActive = false;

  @override
  void initState() {
    super.initState();
    _checkSession();
    // Replicates Kivy's Clock.schedule_interval(self.check_global_network, 3)
    networkTimer = Timer.periodic(
      const Duration(seconds: 3),
      (timer) => _checkGlobalNetwork(),
    );
  }

  @override
  void dispose() {
    networkTimer?.cancel();
    super.dispose();
  }

  Future<void> _checkSession() async {
    final prefs = await SharedPreferences.getInstance();
    final int? sessionTime = prefs.getInt('session_time');
    final String? savedPage = prefs.getString('session_page');

    if (sessionTime != null && savedPage != null) {
      final currentTime = DateTime.now().millisecondsSinceEpoch ~/ 1000;
      if ((currentTime - sessionTime) < 2600) {
        lastScreen = savedPage;
      }
    }

    // Splash Timeout: Replicates Kivy's `Clock.schedule_once(..., 14)`
    Future.delayed(const Duration(seconds: 14), () {
      if (mounted) {
        setState(() {
          currentScreen = lastScreen;
        });
      }
    });
  }

  Future<void> _saveLoginSession() async {
    final prefs = await SharedPreferences.getInstance();
    final currentTime = DateTime.now().millisecondsSinceEpoch ~/ 1000;
    await prefs.setInt('session_time', currentTime);
    await prefs.setString('session_page', 'main_list');
  }

  Future<void> _checkGlobalNetwork() async {
    bool connected = await isConnected();
    if (!connected && !isNetworkErrorActive) {
      if (currentScreen != 'splash') {
        lastScreen = currentScreen;
      }
      setState(() {
        isNetworkErrorActive = true;
      });
    } else if (connected && isNetworkErrorActive) {
      setState(() {
        isNetworkErrorActive = false;
      });
    }
  }

  void navigateTo(String screenName) {
    setState(() {
      currentScreen = screenName;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (isNetworkErrorActive) {
      return const NetworkErrorView();
    }

    switch (currentScreen) {
      case 'splash':
        return const SplashView();
      case 'login':
        return LoginView(
          firebase: firebase,
          onLoginSuccess: () {
            _saveLoginSession();
            navigateTo('success');
          },
          onNavigateToRegister: () => navigateTo('register'),
        );
      case 'register':
        return RegisterView(
          firebase: firebase,
          onRegisterSuccess: () {
            navigateTo('account_success');
          },
          onNavigateToLogin: () => navigateTo('login'),
        );
      case 'account_success':
        return AccountCreatedView(onSignInPressed: () => navigateTo('login'));
      case 'success':
        return SuccessView(onComplete: () => navigateTo('main_list'));
      case 'main_list':
        return MainListView(
          onPredictionComplete: (result) {
            setState(() {
              currentScreen = 'prediction_result';
              predictionData = result;
            });
          },
        );
      case 'prediction_result':
        return PredictionResultView(
          resultText: predictionData,
          onBackHome: () => navigateTo('main_list'),
        );
      default:
        return const SplashView();
    }
  }

  String predictionData = "";
}

// ---------------------------------------------------------
// 3. UI VIEWS (FLUTTER IMPLEMENTATIONS OF KV WIDGETS)
// ---------------------------------------------------------

// --- SPLASH SCREEN ---
class SplashView extends StatelessWidget {
  const SplashView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Container(
          width: 280,
          height: 280,
          decoration: const BoxDecoration(
            color: Colors.white,
            shape: BoxShape.circle,
          ),
          child: Stack(
            alignment: Alignment.center,
            children: [
              Positioned(
                top: 70,
                child: Container(
                  width: 140,
                  height: 140,
                  decoration: const BoxDecoration(
                    color: Color(0xffcc1a1a),
                    shape: BoxShape.circle,
                  ),
                ),
              ),
              CustomPaint(
                size: const Size(140, 115),
                painter: TrianglePainter(),
              ),
              Container(width: 36, height: 10, color: Colors.white),
              Container(width: 10, height: 36, color: Colors.white),
            ],
          ),
        ),
      ),
    );
  }
}

class TrianglePainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = const Color(0xffcc1a1a);
    final path = Path()
      ..moveTo(size.width / 2, 0)
      ..lineTo(0, size.height)
      ..lineTo(size.width, size.height)
      ..close();
    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

// --- NETWORK ERROR VIEW ---
class NetworkErrorView extends StatelessWidget {
  const NetworkErrorView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Container(
          width: MediaQuery.of(context).size.width * 0.85,
          padding: const EdgeInsets.all(30),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(40),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.cloud_off, size: 80, color: Colors.redAccent),
              const SizedBox(height: 20),
              const Text(
                "Please Check Your Network\nConnections",
                textAlign: TextAlign.center,
                style: TextStyle(color: Color(0xff33334d), fontSize: 18),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// --- LOGIN VIEW ---
class LoginView extends StatefulWidget {
  final FirebaseManager firebase;
  final VoidCallback onLoginSuccess;
  final VoidCallback onNavigateToRegister;

  const LoginView({
    required this.firebase,
    required this.onLoginSuccess,
    required this.onNavigateToRegister,
    super.key,
  });

  @override
  State<LoginView> createState() => _LoginViewState();
}

class _LoginViewState extends State<LoginView> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();

  void _login() async {
    String email = _emailController.text.trim();
    String password = _passwordController.text.trim();

    if (email.isEmpty || password.isEmpty) {
      showErrorDialog(context, "!!! Please Enter Email and Password!");
      return;
    }

    final res = await widget.firebase.login(email, password);
    if (res["success"]) {
      widget.onLoginSuccess();
    } else {
      String errMsg = res["data"]["error"]["message"] ?? "INVALID_CREDENTIALS";
      showErrorDialog(context, "Login Failed:\n${errMsg.replaceAll('_', ' ')}");
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: SingleChildScrollView(
          child: Container(
            width: 320,
            padding: const EdgeInsets.all(30),
            decoration: BoxDecoration(
              color: const Color(0xff6633cc),
              borderRadius: BorderRadius.circular(35),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text(
                  "Sign In",
                  style: TextStyle(
                    fontSize: 32,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
                const SizedBox(height: 25),
                _buildInput(_emailController, "Email ID", false),
                const SizedBox(height: 20),
                _buildInput(_passwordController, "Password", true),
                const SizedBox(height: 25),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.white,
                    minimumSize: const Size(double.infinity, 55),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(27.5),
                    ),
                  ),
                  onPressed: _login,
                  child: const Text(
                    "LOGIN",
                    style: TextStyle(
                      color: Color(0xff4d1a99),
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                TextButton(
                  onPressed: widget.onNavigateToRegister,
                  child: const Text(
                    "New here? Create Account",
                    style: TextStyle(color: Colors.white70, fontSize: 14),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildInput(
    TextEditingController controller,
    String hint,
    bool isObscure,
  ) {
    return TextField(
      controller: controller,
      obscureText: isObscure,
      style: const TextStyle(color: Colors.white),
      decoration: InputDecoration(
        hintText: hint,
        hintStyle: const TextStyle(color: Colors.white54),
        filled: true,
        fillColor: Colors.white.withOpacity(0.2),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 15,
          vertical: 15,
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(25),
          borderSide: BorderSide.none,
        ),
      ),
    );
  }
}

// --- REGISTER VIEW ---
class RegisterView extends StatefulWidget {
  final FirebaseManager firebase;
  final VoidCallback onRegisterSuccess;
  final VoidCallback onNavigateToLogin;

  const RegisterView({
    required this.firebase,
    required this.onRegisterSuccess,
    required this.onNavigateToLogin,
    super.key,
  });

  @override
  State<RegisterView> createState() => _RegisterViewState();
}

class _RegisterViewState extends State<RegisterView> {
  final _userController = TextEditingController();
  final _passController = TextEditingController();
  final _gmailController = TextEditingController();
  final _mobileController = TextEditingController();

  void _register() async {
    if (_userController.text.trim().isEmpty ||
        _passController.text.trim().isEmpty ||
        _gmailController.text.trim().isEmpty ||
        _mobileController.text.trim().isEmpty) {
      showErrorDialog(context, "!!! Please Fill All Registration Fields!");
      return;
    }

    final res = await widget.firebase.register(
      _gmailController.text.trim(),
      _passController.text.trim(),
    );
    if (res["success"]) {
      widget.onRegisterSuccess();
    } else {
      String errMsg = res["data"]["error"]["message"] ?? "REGISTRATION_FAILED";
      showErrorDialog(context, "Error: ${errMsg.replaceAll('_', ' ')}");
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: SingleChildScrollView(
          child: Container(
            width: 320,
            padding: const EdgeInsets.all(25),
            decoration: BoxDecoration(
              color: const Color(0xfff5f5fa),
              borderRadius: BorderRadius.circular(35),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Center(
                  child: Text(
                    "Create Account",
                    style: TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.bold,
                      color: Color(0xff5db8db),
                    ),
                  ),
                ),
                const SizedBox(height: 15),
                _formField(
                  "Username",
                  _userController,
                  TextInputType.text,
                  false,
                ),
                _formField(
                  "Password",
                  _passController,
                  TextInputType.text,
                  true,
                ),
                _formField(
                  "Gmail Id",
                  _gmailController,
                  TextInputType.emailAddress,
                  false,
                ),
                _formField(
                  "Mobile No",
                  _mobileController,
                  TextInputType.number,
                  false,
                ),
                const SizedBox(height: 15),
                Center(
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xff5db8db),
                      minimumSize: const Size(240, 50),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                    onPressed: _register,
                    child: const Text(
                      "Create Account",
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ),
                Center(
                  child: TextButton(
                    onPressed: widget.onNavigateToLogin,
                    child: const Text(
                      "Already have an account? Sign In",
                      style: TextStyle(color: Color(0xffe86c8c), fontSize: 14),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _formField(
    String label,
    TextEditingController controller,
    TextInputType type,
    bool isSecure,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(
            color: Colors.grey,
            fontSize: 14,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 4),
        TextField(
          controller: controller,
          keyboardType: type,
          obscureText: isSecure,
          style: const TextStyle(color: Colors.black87),
          decoration: InputDecoration(
            filled: true,
            fillColor: const Color(0xfffef3e6),
            contentPadding: const EdgeInsets.symmetric(
              horizontal: 15,
              vertical: 12,
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
              borderSide: const BorderSide(
                color: Color(0xff5db8db),
                width: 1.1,
              ),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
              borderSide: BorderSide.none,
            ),
          ),
        ),
        const SizedBox(height: 8),
      ],
    );
  }
}

// --- ACCOUNT CREATED VIEW ---
class AccountCreatedView extends StatelessWidget {
  final VoidCallback onSignInPressed;
  const AccountCreatedView({required this.onSignInPressed, super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Container(
          width: 300,
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(40),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.check_circle, size: 80, color: Colors.green),
              const SizedBox(height: 15),
              const Text(
                "Account Created\nSuccessfully",
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 22,
                  color: Color(0xff4d4d1a),
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 10),
              const Text(
                "Go to login your Account",
                style: TextStyle(fontSize: 14, color: Colors.deepOrange),
              ),
              const SizedBox(height: 20),
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xff8000cc),
                  minimumSize: const Size(140, 48),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(24),
                  ),
                ),
                onPressed: onSignInPressed,
                child: const Text(
                  "Sign In",
                  style: TextStyle(color: Colors.white),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// --- SUCCESS TRANSITION VIEW ---
class SuccessView extends StatefulWidget {
  final VoidCallback onComplete;
  const SuccessView({required this.onComplete, super.key});

  @override
  State<SuccessView> createState() => _SuccessViewState();
}

class _SuccessViewState extends State<SuccessView> {
  @override
  void initState() {
    super.initState();
    Future.delayed(const Duration(seconds: 2), widget.onComplete);
  }

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.check_circle_outline,
              size: 120,
              color: Color(0xff2ecc71),
            ),
            SizedBox(height: 20),
            Text(
              "Signed in Successfully",
              style: TextStyle(color: Color(0xffcc6699), fontSize: 20),
            ),
          ],
        ),
      ),
    );
  }
}

// --- MAIN PREDICTION INPUT SCREEN ---
class MainListView extends StatefulWidget {
  final Function(String) onPredictionComplete;
  const MainListView({required this.onPredictionComplete, super.key});

  @override
  State<MainListView> createState() => _MainListViewState();
}

class _MainListViewState extends State<MainListView> {
  final Map<String, TextEditingController> controllers = {
    "Pregnancies": TextEditingController(),
    "Glucose": TextEditingController(),
    "Blood Pressure": TextEditingController(),
    "Skin Thickness": TextEditingController(),
    "Insulin": TextEditingController(),
    "BMI": TextEditingController(),
    "Diabetes Pedigree Function": TextEditingController(),
    "Age": TextEditingController(),
  };

  void _predict() {
    for (var val in controllers.values) {
      if (val.text.trim().isEmpty) {
        showErrorDialog(context, "All fields are required!");
        return;
      }
    }

    try {
      double glucose = double.parse(controllers["Glucose"]!.text.trim());
      double bmi = double.parse(controllers["BMI"]!.text.trim());
      double age = double.parse(controllers["Age"]!.text.trim());

      int score = 0;
      if (glucose > 140) score += 2;
      if (glucose > 180) score += 3;
      if (bmi > 30) score += 1;
      if (bmi > 35) score += 2;
      if (age > 45) score += 1;

      String result = (score >= 3)
          ? "Positive (High Risk)"
          : "Negative (Low Risk)";
      widget.onPredictionComplete(result);
    } catch (_) {
      showErrorDialog(context, "Invalid Numeric Data!");
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Container(
          width: MediaQuery.of(context).size.width * 0.9,
          height: MediaQuery.of(context).size.height * 0.9,
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: const Color(0xfff2f5f9),
            borderRadius: BorderRadius.circular(40),
          ),
          child: Column(
            children: [
              const Text(
                "Diabetes Prediction",
                style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.bold,
                  color: Colors.black87,
                ),
              ),
              const SizedBox(height: 15),
              Expanded(
                child: ListView(
                  children: controllers.keys
                      .map(
                        (title) =>
                            _buildPlaceholderBox(title, controllers[title]!),
                      )
                      .toList(),
                ),
              ),
              const SizedBox(height: 15),
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xff222222),
                  minimumSize: const Size(200, 55),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(20),
                  ),
                ),
                onPressed: _predict,
                child: const Text(
                  "Predict",
                  style: TextStyle(
                    color: Color(0xffcc6680),
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildPlaceholderBox(String title, TextEditingController controller) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(25),
        gradient: const LinearGradient(
          colors: [Color(0xff1a66e6), Color(0xff9933cc)],
        ),
      ),
      child: TextField(
        controller: controller,
        keyboardType: const TextInputType.numberWithOptions(decimal: true),
        style: const TextStyle(color: Colors.white),
        decoration: InputDecoration(
          hintText: title,
          hintStyle: const TextStyle(color: Colors.white70),
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 15,
            vertical: 12,
          ),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(25),
            borderSide: BorderSide.none,
          ),
        ),
      ),
    );
  }
}

// --- PREDICTION RESULT VIEW ---
class PredictionResultView extends StatelessWidget {
  final String resultText;
  final VoidCallback onBackHome;

  const PredictionResultView({
    required this.resultText,
    required this.onBackHome,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Container(
          width: 320,
          height: 350,
          padding: const EdgeInsets.all(30),
          decoration: BoxDecoration(
            color: const Color(0xfff2f5f9),
            borderRadius: BorderRadius.circular(35),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              const Text(
                "Prediction Result",
                style: TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                  color: Colors.black87,
                ),
              ),
              Text(
                resultText,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 22,
                  color: Color(0xff4d1a99),
                  fontWeight: FontWeight.bold,
                ),
              ),
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xff5db8db),
                  minimumSize: const Size(double.infinity, 55),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(27.5),
                  ),
                ),
                onPressed: onBackHome,
                child: const Text(
                  "Back to Home",
                  style: TextStyle(color: Colors.white, fontSize: 16),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------
// 4. ERROR OVERLAY COMPONENT
// ---------------------------------------------------------
void showErrorDialog(BuildContext context, String message) {
  showDialog(
    context: context,
    barrierDismissible: false,
    builder: (context) {
      // Replicates the 2-second timeout screen inside Kivy Error Handlers
      Future.delayed(const Duration(seconds: 2), () {
        Navigator.of(context).pop();
      });
      return Dialog(
        backgroundColor: const Color(0xff23102f),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(40)),
        child: Container(
          width: 320,
          height: 400,
          padding: const EdgeInsets.all(30),
          color: Colors.white,
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.error_outline, size: 100, color: Colors.red),
              const SizedBox(height: 20),
              Text(
                message,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: Colors.redAccent,
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
        ),
      );
    },
  );
}
