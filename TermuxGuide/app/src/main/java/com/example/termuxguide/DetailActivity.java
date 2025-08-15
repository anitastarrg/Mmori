package com.example.termuxguide;

import android.app.Activity;
import android.os.Bundle;
import android.widget.TextView;

public class DetailActivity extends Activity {
	@Override
	protected void onCreate(Bundle savedInstanceState) {
		super.onCreate(savedInstanceState);
		setContentView(R.layout.activity_detail);

		TextView nameTv = findViewById(R.id.commandNameTextView);
		TextView descTv = findViewById(R.id.commandDescTextView);
		TextView exTv = findViewById(R.id.commandExamplesTextView);

		String name = getIntent().getStringExtra("name");
		String description = getIntent().getStringExtra("description");
		String examples = getIntent().getStringExtra("examples");

		nameTv.setText(name);
		descTv.setText(description);
		exTv.setText(examples);
	}
}