# DonateTrack Analytics — Android wrapper

This Android app opens the existing Streamlit DonateTrack website inside an Android WebView. The APK does **not** run the Python/SQLite backend on the phone. Deploy the Streamlit site first, then enter its HTTPS URL the first time the app opens. The URL is saved on the device and can be changed from the app menu (`⋮` → Configure website).

## Build an APK through GitHub Actions

1. Push this repository, including the `android/` folder and `.github/workflows/build-android-apk.yml`, to GitHub.
2. Open the repository's **Actions** tab.
3. Select **Build DonateTrack Android APK**.
4. Click **Run workflow** (or push a change under `android/`).
5. Open the completed run and download the `DonateTrack-Analytics-debug-apk` artifact.
6. Extract the downloaded artifact; it contains `app-debug.apk`.
7. Transfer the APK to an Android phone and install it. You may need to allow installation from that file manager/browser.

## Build locally (Android Studio)

Open the `android/` directory as a project in Android Studio and build the `app` debug variant. The project uses Android Gradle Plugin 8.7.3, Gradle 8.9, Java 17, compile SDK 35, and minimum Android API 23.

## Notes

- This is a debug APK for testing, not a signed Play Store release.
- Internet access is required.
- The website must be deployed and reachable over HTTPS.
- Streamlit Community Cloud local SQLite storage can be ephemeral; use persistent storage for important data.
- Use only demonstration payments unless a real payment gateway has been integrated and verified server-side.
