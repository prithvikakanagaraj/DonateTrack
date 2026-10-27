# DonateTrack APK build quick guide

The Android wrapper and GitHub Actions workflow are included in this repository.

1. Deploy the Streamlit app first and copy its public HTTPS URL.
2. Push the whole project folder to GitHub, including `.github/workflows/build-android-apk.yml` and `android/`.
3. Open **Actions** → **Build DonateTrack Android APK** → **Run workflow**.
4. When the workflow finishes successfully, download the `DonateTrack-Analytics-debug-apk` artifact from the run's Artifacts section.
5. Extract `app-debug.apk` and install it on your Android device.
6. On first launch, enter the deployed Streamlit URL.

This environment does not contain the Android SDK or Gradle, so a binary APK was not compiled here. GitHub Actions will compile it in the repository after you upload these files.
