const r = await fetch("https://api.openai.com/v1/audio/translations", { method: "POST", body: form });
const job = await openai.fine_tuning.jobs.create({ model: "gpt-4.1", training_file: fileId });
