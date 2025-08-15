package com.example.termuxguide;

import android.content.Context;
import android.content.Intent;
import android.content.res.AssetManager;
import android.os.Bundle;
import android.app.AlertDialog;
import android.app.Activity;
import android.content.DialogInterface;
import android.content.ClipboardManager;
import android.content.ClipData;
import android.text.TextUtils;
import android.view.View;
import android.view.ViewGroup;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.ListView;
import android.widget.SearchView;
import android.widget.Spinner;
import android.widget.TextView;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

public class MainActivity extends Activity {

    private SearchView searchView;
    private ListView listView;
    private Spinner spinnerCategory;
    private TextView emptyView;

    private CommandAdapter listAdapter;
    private final List<Command> allCommands = new ArrayList<Command>();
    private final List<Command> visibleCommands = new ArrayList<Command>();
    private final List<String> categories = new ArrayList<String>();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        searchView = findViewById(R.id.search_view);
        spinnerCategory = findViewById(R.id.spinner_category);
        listView = findViewById(R.id.list_view);
        emptyView = findViewById(R.id.empty_view);

        loadCommandsFromAssets(this);
        sortCommandsByName();
        buildCategories();

        listAdapter = new CommandAdapter(this, visibleCommands);
        listView.setAdapter(listAdapter);
        listView.setEmptyView(emptyView);

        listView.setOnItemClickListener(new AdapterView.OnItemClickListener() {
            @Override
            public void onItemClick(AdapterView<?> parent, View view, int position, long id) {
                Command cmd = visibleCommands.get(position);
                showDetailsDialog(cmd);
            }
        });

        searchView.setOnQueryTextListener(new SearchView.OnQueryTextListener() {
            @Override
            public boolean onQueryTextSubmit(String query) {
                applyFilter(query, (String) spinnerCategory.getSelectedItem());
                return true;
            }

            @Override
            public boolean onQueryTextChange(String newText) {
                applyFilter(newText, (String) spinnerCategory.getSelectedItem());
                return true;
            }
        });

        ArrayAdapter<String> catAdapter = new ArrayAdapter<String>(this, android.R.layout.simple_spinner_item, categories);
        catAdapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        spinnerCategory.setAdapter(catAdapter);
        spinnerCategory.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                applyFilter(searchView.getQuery().toString(), categories.get(position));
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) { }
        });

        // Начальная фильтрация после установки адаптеров
        if (!categories.isEmpty()) {
            applyFilter("", categories.get(0));
        }
    }

    private void buildCategories() {
        Set<String> set = new LinkedHashSet<String>();
        set.add(getString(R.string.all));
        for (Command c : allCommands) {
            if (!TextUtils.isEmpty(c.category)) set.add(c.category);
        }
        categories.clear();
        categories.addAll(set);
    }

    private void applyFilter(String query, String category) {
        visibleCommands.clear();
        String q = query == null ? "" : query.trim().toLowerCase();
        boolean all = TextUtils.equals(category, getString(R.string.all));
        for (Command cmd : allCommands) {
            if (!all && !TextUtils.equals(cmd.category, category)) continue;
            if (TextUtils.isEmpty(q)) {
                visibleCommands.add(cmd);
            } else {
                String hay = (cmd.name + " " + cmd.shortDescription + " " + cmd.syntax + " " + cmd.examples + " " + cmd.notes + " " + cmd.packageName + " " + cmd.category).toLowerCase();
                if (hay.contains(q)) visibleCommands.add(cmd);
            }
        }
        listAdapter.notifyDataSetChanged();
    }

    private void showDetailsDialog(final Command command) {
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
            message.append("Пакет: ").append(command.packageName).append("\n");
        }
        if (!TextUtils.isEmpty(command.category)) {
            message.append("Категория: ").append(command.category);
        }

        AlertDialog.Builder b = new AlertDialog.Builder(this)
                .setTitle(command.name)
                .setMessage(message.toString().trim())
                .setPositiveButton(android.R.string.ok, null)
                .setNeutralButton(getString(R.string.share), new DialogInterface.OnClickListener() {
                    public void onClick(DialogInterface dialog, int which) {
                        shareCommand(command);
                    }
                });
        if (!TextUtils.isEmpty(command.examples)) {
            b.setNegativeButton(getString(R.string.copy_example), new DialogInterface.OnClickListener() {
                public void onClick(DialogInterface dialog, int which) {
                    copyToClipboard(command.examples);
                }
            });
        } else if (!TextUtils.isEmpty(command.syntax)) {
            b.setNegativeButton(getString(R.string.copy_syntax), new DialogInterface.OnClickListener() {
                public void onClick(DialogInterface dialog, int which) {
                    copyToClipboard(command.syntax);
                }
            });
        }
        b.show();
    }

    private void shareCommand(Command c) {
        StringBuilder sb = new StringBuilder();
        sb.append(c.name).append("\n");
        if (!TextUtils.isEmpty(c.syntax)) sb.append(c.syntax).append("\n");
        if (!TextUtils.isEmpty(c.examples)) sb.append(c.examples).append("\n");
        Intent sendIntent = new Intent(Intent.ACTION_SEND);
        sendIntent.setType("text/plain");
        sendIntent.putExtra(Intent.EXTRA_TEXT, sb.toString().trim());
        startActivity(Intent.createChooser(sendIntent, getString(R.string.share)));
    }

    private void copyToClipboard(String text) {
        ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
        if (cm != null) {
            cm.setPrimaryClip(ClipData.newPlainText("text", text));
        }
    }

    private void sortCommandsByName() {
        Collections.sort(allCommands, new Comparator<Command>() {
            @Override
            public int compare(Command a, Command b) {
                return a.name.compareToIgnoreCase(b.name);
            }
        });
    }

    private void loadCommandsFromAssets(Context context) {
        allCommands.clear();
        String json = readAssetText(context.getAssets(), "commands.json");
        if (TextUtils.isEmpty(json)) return;
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
        List<String> out = new ArrayList<String>();
        if (TextUtils.isEmpty(json)) return out;
        int i = 0;
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
        c.category = extractString(obj, "category");
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
        String category;
    }

    private static class CommandAdapter extends ArrayAdapter<Command> {
        private final List<Command> items;

        CommandAdapter(Context ctx, List<Command> items) {
            super(ctx, 0, items);
            this.items = items;
        }

        @Override
        public View getView(int position, View convertView, ViewGroup parent) {
            View v = convertView;
            if (v == null) {
                v = View.inflate(getContext(), R.layout.item_command, null);
            }
            TextView title = v.findViewById(R.id.text_title);
            TextView subtitle = v.findViewById(R.id.text_subtitle);
            TextView cat = v.findViewById(R.id.text_category);
            Command c = items.get(position);
            title.setText(c.name);
            subtitle.setText(TextUtils.isEmpty(c.shortDescription) ? "" : c.shortDescription);
            if (TextUtils.isEmpty(c.category)) {
                cat.setVisibility(View.GONE);
            } else {
                cat.setVisibility(View.VISIBLE);
                cat.setText(c.category);
            }
            return v;
        }
    }
}