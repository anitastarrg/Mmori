package com.example.termuxguide;

import android.content.Context;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.BaseAdapter;
import android.widget.TextView;

import java.util.ArrayList;
import java.util.List;

public class CommandsAdapter extends BaseAdapter {
	private final Context context;
	private final LayoutInflater inflater;
	private final List<Command> allCommands;
	private final List<Command> filteredCommands;

	public CommandsAdapter(Context context, List<Command> commands) {
		this.context = context;
		this.inflater = LayoutInflater.from(context);
		this.allCommands = new ArrayList<>(commands);
		this.filteredCommands = new ArrayList<>(commands);
	}

	public void filter(String query) {
		filteredCommands.clear();
		if (query == null || query.trim().isEmpty()) {
			filteredCommands.addAll(allCommands);
		} else {
			String q = query.toLowerCase();
			for (Command c : allCommands) {
				if ((c.name != null && c.name.toLowerCase().contains(q)) ||
					(c.description != null && c.description.toLowerCase().contains(q))) {
					filteredCommands.add(c);
				}
			}
		}
		notifyDataSetChanged();
	}

	@Override
	public int getCount() {
		return filteredCommands.size();
	}

	@Override
	public Object getItem(int position) {
		return filteredCommands.get(position);
	}

	@Override
	public long getItemId(int position) {
		return position;
	}

	@Override
	public View getView(int position, View convertView, ViewGroup parent) {
		ViewHolder holder;
		if (convertView == null) {
			convertView = inflater.inflate(R.layout.list_item_command, parent, false);
			holder = new ViewHolder();
			holder.nameTextView = convertView.findViewById(R.id.nameTextView);
			holder.descTextView = convertView.findViewById(R.id.descTextView);
			convertView.setTag(holder);
		} else {
			holder = (ViewHolder) convertView.getTag();
		}

		Command c = filteredCommands.get(position);
		holder.nameTextView.setText(c.name);
		holder.descTextView.setText(c.description);
		return convertView;
	}

	private static class ViewHolder {
		TextView nameTextView;
		TextView descTextView;
	}
}