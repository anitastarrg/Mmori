package com.example.termuxguide;

import android.content.Context;
import android.content.res.AssetManager;
import android.os.Bundle;
import android.app.AlertDialog;
import android.app.Activity;
import android.text.TextUtils;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.ListView;
import android.widget.SearchView;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;

public class MainActivity extends Activity {

    private SearchView searchView;
    private ListView listView;

    private ArrayAdapter<String> listAdapter;
    private final List<Command> allCommands = new ArrayList<Command>();
    private final List<String> visibleItems = new ArrayList<String>();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        searchView = findViewById(R.id.search_view);
        listView = findViewById(R.id.list_view);

        loadCommandsFromAssets(this);
        sortCommandsByName();
        rebuildVisibleItems("");

        listAdapter = new ArrayAdapter<String>(this, android.R.layout.simple_list_item_1, visibleItems);
        listView.setAdapter(listAdapter);

        listView.setOnItemClickListener(new AdapterView.OnItemClickListener() {
            @Override
            public void onItemClick(AdapterView<?> parent, View view, int position, long id) {
                String item = visibleItems.get(position);
                showDetailsDialog(item);
            }
        });

        searchView.setOnQueryTextListener(new SearchView.OnQueryTextListener() {
            @Override
            public boolean onQueryTextSubmit(String query) {
                filterList(query);
                return true;
            }

            @Override
            public boolean onQueryTextChange(String newText) {
                filterList(newText);
                return true;
            }
        });
    }

    private void filterList(String query) {
        rebuildVisibleItems(query);
        listAdapter.notifyDataSetChanged();
    }

    private void showDetailsDialog(String listItemText) {
        // listItemText format: "command — short"
        String name = listItemText;
        int sep = listItemText.indexOf(" — ");
        if (sep != -1) {
            name = listItemText.substring(0, sep);
        }
        Command command = findByName(name);
        if (command == null) return;

        StringBuilder message = new StringBuilder();
        if (!TextUtils.isEmpty(command.shortDescription)) {
            message.append(command.shortDescription).append("\n\n");
        }
        if (!TextUtils.isEmpty(command.syntax)) {
            message.append("Синтаксис: \n").append(command.syntax).append("\n\n");
        }
        if (!TextUtils.isEmpty(command.examples)) {
            message.append("Примеры: \n").append(command.examples).append("\n\n");
        }
        if (!TextUtils.isEmpty(command.notes)) {
            message.append("Заметки: \n").append(command.notes).append("\n\n");
        }
        if (!TextUtils.isEmpty(command.packageName)) {
            message.append("Пакет: ").append(command.packageName);
        }

        new AlertDialog.Builder(this)
                .setTitle(command.name)
                .setMessage(message.toString().trim())
                .setPositiveButton(android.R.string.ok, null)
                .show();
    }

    private void sortCommandsByName() {
        Collections.sort(allCommands, new Comparator<Command>() {
            @Override
            public int compare(Command a, Command b) {
                return a.name.compareToIgnoreCase(b.name);
            }
        });
    }

    private void rebuildVisibleItems(String query) {
        visibleItems.clear();
        String q = query == null ? "" : query.trim().toLowerCase();
        for (Command cmd : allCommands) {
            String row = cmd.name + " — " + (TextUtils.isEmpty(cmd.shortDescription) ? "" : cmd.shortDescription);
            if (TextUtils.isEmpty(q)) {
                visibleItems.add(row);
            } else {
                String hay = (cmd.name + " " + cmd.shortDescription + " " + cmd.syntax + " " + cmd.examples + " " + cmd.notes + " " + cmd.packageName).toLowerCase();
                if (hay.contains(q)) {
                    visibleItems.add(row);
                }
            }
        }
        if (visibleItems.isEmpty()) {
            visibleItems.add(getString(R.string.no_results));
        }
    }

    private Command findByName(String name) {
        for (Command c : allCommands) {
            if (c.name.equalsIgnoreCase(name)) return c;
        }
        return null;
    }

    private void loadCommandsFromAssets(Context context) {
        allCommands.clear();
        String json = readAssetText(context.getAssets(), "commands.json");
        if (TextUtils.isEmpty(json)) return;
        // Very small and AIDE-safe JSON parse (manual) expecting array of objects with fixed keys
        // Format: [{"name":"apt","short":"...","syntax":"...","examples":"...","notes":"...","package":"..."}, ...]
        List<String> objects = splitTopLevelObjects(json);
        for (String obj : objects) {
            Command c = parseCommandObject(obj);
            if (c != null && !TextUtils.isEmpty(c.name)) {
                allCommands.add(c);
            }
        }
    }

    private String readAssetText(AssetManager am, String fileName) {
        StringBuilder sb = new StringBuilder();
        InputStream is = null;
        BufferedReader br = null;
        try {
            is = am.open(fileName);
            br = new BufferedReader(new InputStreamReader(is, "UTF-8"));
            String line;
            while ((line = br.readLine()) != null) {
                sb.append(line);
            }
        } catch (IOException e) {
            // ignore
        } finally {
            try { if (br != null) br.close(); } catch (IOException ignored) {}
            try { if (is != null) is.close(); } catch (IOException ignored) {}
        }
        return sb.toString();
    }

    private List<String> splitTopLevelObjects(String json) {
        List<String> out = new ArrayList<>();
        if (TextUtils.isEmpty(json)) return out;
        int i = 0;
        // skip spaces
        while (i < json.length() && Character.isWhitespace(json.charAt(i))) i++;
        if (i >= json.length() || json.charAt(i) != '[') return out;
        i++;
        int brace = 0;
        int start = -1;
        boolean inString = false;
        while (i < json.length()) {
            char ch = json.charAt(i);
            if (ch == '"' && (i == 0 || json.charAt(i - 1) != '\\')) {
                inString = !inString;
            }
            if (!inString) {
                if (ch == '{') {
                    if (brace == 0) start = i;
                    brace++;
                } else if (ch == '}') {
                    brace--;
                    if (brace == 0 && start != -1) {
                        out.add(json.substring(start, i + 1));
                        start = -1;
                    }
                }
            }
            i++;
        }
        return out;
    }

    private Command parseCommandObject(String obj) {
        Command c = new Command();
        c.name = extractString(obj, "name");
        c.shortDescription = extractString(obj, "short");
        c.syntax = extractString(obj, "syntax");
        c.examples = extractString(obj, "examples");
        c.notes = extractString(obj, "notes");
        c.packageName = extractString(obj, "package");
        return c;
    }

    private String extractString(String obj, String key) {
        String pattern = "\"" + key + "\"";
        int idx = obj.indexOf(pattern);
        if (idx == -1) return "";
        idx = obj.indexOf(':', idx);
        if (idx == -1) return "";
        int startQuote = obj.indexOf('"', idx + 1);
        if (startQuote == -1) return "";
        StringBuilder value = new StringBuilder();
        boolean escape = false;
        for (int i = startQuote + 1; i < obj.length(); i++) {
            char ch = obj.charAt(i);
            if (escape) {
                switch (ch) {
                    case 'n': value.append('\n'); break;
                    case 'r': value.append('\r'); break;
                    case 't': value.append('\t'); break;
                    case '"': value.append('"'); break;
                    case '\\': value.append('\\'); break;
                    default: value.append(ch); break;
                }
                escape = false;
            } else if (ch == '\\') {
                escape = true;
            } else if (ch == '"') {
                break;
            } else {
                value.append(ch);
            }
        }
        return value.toString();
    }

    static class Command {
        String name;
        String shortDescription;
        String syntax;
        String examples;
        String notes;
        String packageName;
    }
}