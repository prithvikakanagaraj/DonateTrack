package com.donatetrack.analytics;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.net.Uri;
import android.os.Bundle;
import android.view.Menu;
import android.view.MenuItem;
import android.view.View;
import android.view.Window;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

public class MainActivity extends Activity {
    private static final String PREFS = "donatetrack_settings";
    private static final String KEY_URL = "website_url";
    private WebView webView;
    private ProgressBar progressBar;
    private TextView statusText;
    private SharedPreferences prefs;

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        getWindow().setStatusBarColor(0xFF14532D);
        getWindow().setNavigationBarColor(0xFF14532D);
        buildLayout();
        String url = prefs.getString(KEY_URL, "");
        if (url == null || url.trim().isEmpty()) {
            showUrlDialog(true);
        } else {
            loadWebsite(url);
        }
    }

    private void buildLayout() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(0xFFF7FAF7);

        LinearLayout toolbar = new LinearLayout(this);
        toolbar.setOrientation(LinearLayout.HORIZONTAL);
        toolbar.setGravity(android.view.Gravity.CENTER_VERTICAL);
        toolbar.setPadding(12, 8, 12, 8);
        toolbar.setBackgroundColor(0xFF14532D);
        TextView appTitle = new TextView(this);
        appTitle.setText("DonateTrack Analytics");
        appTitle.setTextColor(0xFFFFFFFF);
        appTitle.setTextSize(17);
        appTitle.setTypeface(null, android.graphics.Typeface.BOLD);
        toolbar.addView(appTitle, new LinearLayout.LayoutParams(0, -2, 1));
        Button configureButton = new Button(this);
        configureButton.setText("Website");
        configureButton.setOnClickListener(v -> showUrlDialog(false));
        toolbar.addView(configureButton, new LinearLayout.LayoutParams(-2, -2));
        Button reloadButton = new Button(this);
        reloadButton.setText("Reload");
        reloadButton.setOnClickListener(v -> { if (webView != null) webView.reload(); });
        toolbar.addView(reloadButton, new LinearLayout.LayoutParams(-2, -2));
        root.addView(toolbar, new LinearLayout.LayoutParams(-1, -2));

        progressBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progressBar.setMax(100);
        progressBar.setProgressTintList(android.content.res.ColorStateList.valueOf(0xFF15803D));
        root.addView(progressBar, new LinearLayout.LayoutParams(-1, 4));

        webView = new WebView(this);
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true); // Required by Streamlit
        settings.setDomStorageEnabled(true); // Required by Streamlit sessions/UI
        settings.setLoadsImagesAutomatically(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        webView.setWebChromeClient(new WebChromeClient() {
            @Override public void onProgressChanged(WebView view, int newProgress) {
                progressBar.setProgress(newProgress);
                progressBar.setVisibility(newProgress >= 100 ? View.GONE : View.VISIBLE);
            }
        });
        webView.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                String scheme = uri.getScheme() == null ? "" : uri.getScheme();
                if ("https".equalsIgnoreCase(scheme) || "http".equalsIgnoreCase(scheme)) {
                    String host = uri.getHost() == null ? "" : uri.getHost();
                    if (host.equalsIgnoreCase("streamlit.app") || host.endsWith(".streamlit.app") || host.equalsIgnoreCase("localhost")) {
                        return false;
                    }
                    // Keep normal web navigation in the app; non-web schemes are opened externally below.
                    return false;
                }
                try { startActivity(new Intent(Intent.ACTION_VIEW, uri)); } catch (Exception ignored) {}
                return true;
            }
            @Override public void onPageStarted(WebView view, String url, Bitmap favicon) {
                progressBar.setVisibility(View.VISIBLE);
                statusText.setVisibility(View.GONE);
            }
            @Override public void onReceivedError(WebView view, WebResourceRequest request, android.webkit.WebResourceError error) {
                if (request.isForMainFrame()) {
                    statusText.setText("Unable to load DonateTrack. Check your internet connection and website URL, then use ⋮ > Configure website.");
                    statusText.setVisibility(View.VISIBLE);
                }
            }
        });
        root.addView(webView, new LinearLayout.LayoutParams(-1, 0, 1));

        statusText = new TextView(this);
        statusText.setTextColor(0xFF14532D);
        statusText.setTextSize(15);
        statusText.setPadding(24, 16, 24, 16);
        statusText.setVisibility(View.GONE);
        root.addView(statusText, new LinearLayout.LayoutParams(-1, -2));
        setContentView(root);
    }

    private void loadWebsite(String rawUrl) {
        String url = rawUrl == null ? "" : rawUrl.trim();
        if (!url.startsWith("https://") && !url.startsWith("http://")) url = "https://" + url;
        Uri uri = Uri.parse(url);
        if (uri.getHost() == null || uri.getHost().trim().isEmpty()) {
            Toast.makeText(this, "Enter a valid website URL.", Toast.LENGTH_LONG).show();
            showUrlDialog(false);
            return;
        }
        prefs.edit().putString(KEY_URL, url).apply();
        statusText.setVisibility(View.GONE);
        webView.loadUrl(url);
    }

    private void showUrlDialog(boolean firstRun) {
        final EditText input = new EditText(this);
        input.setSingleLine(true);
        input.setHint("https://your-app.streamlit.app");
        input.setText(prefs.getString(KEY_URL, ""));
        input.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_URI);
        LinearLayout box = new LinearLayout(this);
        box.setPadding(24, 8, 24, 0);
        box.addView(input, new LinearLayout.LayoutParams(-1, -2));
        new AlertDialog.Builder(this)
            .setTitle(firstRun ? "Connect DonateTrack" : "Configure website")
            .setMessage("Deploy your Streamlit project first, then enter its public HTTPS URL. The URL is saved on this device.")
            .setView(box)
            .setCancelable(!firstRun)
            .setPositiveButton("Open website", (dialog, which) -> loadWebsite(input.getText().toString()))
            .setNegativeButton(firstRun ? "Exit" : "Cancel", (dialog, which) -> { if (firstRun && prefs.getString(KEY_URL, "").isEmpty()) finish(); })
            .show();
    }

    @Override public boolean onCreateOptionsMenu(Menu menu) {
        menu.add("Configure website").setShowAsAction(MenuItem.SHOW_AS_ACTION_NEVER);
        menu.add("Reload").setShowAsAction(MenuItem.SHOW_AS_ACTION_NEVER);
        return true;
    }

    @Override public boolean onOptionsItemSelected(MenuItem item) {
        if ("Configure website".contentEquals(item.getTitle())) { showUrlDialog(false); return true; }
        if ("Reload".contentEquals(item.getTitle())) { if (webView != null) webView.reload(); return true; }
        return super.onOptionsItemSelected(item);
    }

    @Override public void onBackPressed() {
        if (webView != null && webView.canGoBack()) webView.goBack();
        else super.onBackPressed();
    }

    @Override protected void onDestroy() {
        if (webView != null) { webView.stopLoading(); webView.destroy(); webView = null; }
        super.onDestroy();
    }
}
