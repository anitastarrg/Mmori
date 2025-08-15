package com.example.termuxguide;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.text.Editable;
import android.text.TextWatcher;
import android.widget.AdapterView;
import android.widget.EditText;
import android.widget.ListView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.List;

public class MainActivity extends Activity {
	private CommandsAdapter adapter;
	private final List<Command> commands = new ArrayList<>();

	@Override
	protected void onCreate(Bundle savedInstanceState) {
		super.onCreate(savedInstanceState);
		setContentView(R.layout.activity_main);

		EditText searchEditText = findViewById(R.id.searchEditText);
		ListView listView = findViewById(R.id.commandsListView);
		android.widget.TextView emptyView = findViewById(R.id.emptyTextView);
		listView.setEmptyView(emptyView);

		loadCommandsFromAssets();
		adapter = new CommandsAdapter(this, commands);
		listView.setAdapter(adapter);

		listView.setOnItemClickListener(new AdapterView.OnItemClickListener() {
			@Override
			public void onItemClick(AdapterView<?> parent, android.view.View view, int position, long id) {
				Command c = (Command) adapter.getItem(position);
				Intent intent = new Intent(MainActivity.this, DetailActivity.class);
				intent.putExtra("name", c.name);
				intent.putExtra("description", c.description);
				intent.putExtra("examples", c.examples);
				startActivity(intent);
			}
		});

		searchEditText.addTextChangedListener(new TextWatcher() {
			@Override
			public void beforeTextChanged(CharSequence s, int start, int count, int after) { }

			@Override
			public void onTextChanged(CharSequence s, int start, int before, int count) {
				adapter.filter(s.toString());
			}

			@Override
			public void afterTextChanged(Editable s) { }
		});
	}

	private void loadCommandsFromAssets() {
		try {
			InputStream is = getAssets().open("commands.json");
			BufferedReader br = new BufferedReader(new InputStreamReader(is, "UTF-8"));
			StringBuilder sb = new StringBuilder();
			String line;
			while ((line = br.readLine()) != null) {
				sb.append(line);
			}
			br.close();
			JSONArray arr = new JSONArray(sb.toString());
			for (int i = 0; i < arr.length(); i++) {
				JSONObject o = arr.getJSONObject(i);
				commands.add(new Command(
					o.optString("name"),
					o.optString("description"),
					o.optString("examples")
				));
			}
		} catch (Exception e) {
			// Swallow for AIDE simplicity
		}
	}
}