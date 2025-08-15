package com.example.termuxguide;

import android.app.Activity;
import android.os.Bundle;
import android.widget.TextView;

public class DetailActivity extends Activity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_detail);

        TextView titleText = (TextView) findViewById(R.id.titleText);
        TextView usageText = (TextView) findViewById(R.id.usageText);
        TextView descriptionText = (TextView) findViewById(R.id.descriptionText);
        TextView examplesText = (TextView) findViewById(R.id.examplesText);

        String name = getIntent().getStringExtra("name");
        String usage = getIntent().getStringExtra("usage");
        String description = getIntent().getStringExtra("description");
        String examples = getIntent().getStringExtra("examples");

        if (name != null) titleText.setText(name);
        if (usage != null) usageText.setText(usage);
        if (description != null) descriptionText.setText(description);
        if (examples != null) examplesText.setText(examples);
    }
}