package com.example.termuxguide;

public class Command {
	public String name;
	public String description;
	public String examples;

	public Command(String name, String description, String examples) {
		this.name = name;
		this.description = description;
		this.examples = examples;
	}
}