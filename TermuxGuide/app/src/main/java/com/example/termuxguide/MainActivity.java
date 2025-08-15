package com.example.termuxguide;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.text.TextUtils;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.ListView;
import android.widget.SearchView;
import android.widget.TextView;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class MainActivity extends Activity {

    private SearchView searchView;
    private ListView listView;
    private TextView emptyView;

    private ArrayAdapter<String> adapter;
    private List<String> commandNames = new ArrayList<String>();
    private Map<String, JSONObject> nameToCommand = new HashMap<String, JSONObject>();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        searchView = (SearchView) findViewById(R.id.searchView);
        listView = (ListView) findViewById(R.id.listView);
        emptyView = (TextView) findViewById(R.id.emptyView);

        loadCommands();

        adapter = new ArrayAdapter<String>(this, android.R.layout.simple_list_item_1, commandNames);
        listView.setAdapter(adapter);
        listView.setEmptyView(emptyView);

        listView.setOnItemClickListener(new AdapterView.OnItemClickListener() {
            @Override
            public void onItemClick(AdapterView<?> parent, View view, int position, long id) {
                String name = adapter.getItem(position);
                if (name != null) {
                    JSONObject obj = nameToCommand.get(name);
                    Intent intent = new Intent(MainActivity.this, DetailActivity.class);
                    if (obj != null) {
                        intent.putExtra("name", obj.optString("name"));
                        intent.putExtra("usage", obj.optString("usage"));
                        intent.putExtra("description", obj.optString("description"));
                        intent.putExtra("examples", obj.optString("examples"));
                    } else {
                        intent.putExtra("name", name);
                    }
                    startActivity(intent);
                }
            }
        });

        searchView.setOnQueryTextListener(new SearchView.OnQueryTextListener() {
            @Override
            public boolean onQueryTextSubmit(String query) {
                filter(query);
                return true;
            }

            @Override
            public boolean onQueryTextChange(String newText) {
                filter(newText);
                return true;
            }
        });
    }

    private void filter(String query) {
        if (TextUtils.isEmpty(query)) {
            adapter.getFilter().filter(null);
        } else {
            adapter.getFilter().filter(query);
        }
    }

    private void loadCommands() {
        nameToCommand.clear();
        commandNames.clear();
        try {
            String jsonString = readAsset("commands.json");
            JSONArray array = new JSONArray(jsonString);
            for (int i = 0; i < array.length(); i++) {
                JSONObject obj = array.getJSONObject(i);
                String name = obj.optString("name");
                if (!TextUtils.isEmpty(name)) {
                    nameToCommand.put(name, obj);
                    commandNames.add(name);
                }
            }
            Collections.sort(commandNames, new Comparator<String>() {
                @Override
                public int compare(String o1, String o2) {
                    return o1.compareToIgnoreCase(o2);
                }
            });
        } catch (IOException e) {
            e.printStackTrace();
        } catch (JSONException e) {
            e.printStackTrace();
        }
    }

    private String readAsset(String filename) throws IOException {
        InputStream is = null;
        BufferedReader reader = null;
        try {
            is = getAssets().open(filename);
            reader = new BufferedReader(new InputStreamReader(is, "UTF-8"));
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                sb.append(line);
            }
            return sb.toString();
        } finally {
            if (reader != null) {
                try { reader.close(); } catch (IOException ignore) {}
            }
            if (is != null) {
                try { is.close(); } catch (IOException ignore) {}
            }
        }
    }
}