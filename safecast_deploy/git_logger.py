import datetime
import git
import json
import os
import tempfile


class Iso8601DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.datetime)):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


def log_result(result):
    with tempfile.TemporaryDirectory() as temp_dir:
        repo = git.Repo.clone_from('git@github.com:Safecast/deployment-history.git', temp_dir)
        # TODO automatically create dirs and files as necessary
        if isinstance(result, list):
            for item in result:
                write_entry(item, temp_dir, repo)
        else:
            write_entry(result, temp_dir, repo)
        repo.index.commit("Updated entry.")
        repo.remotes.origin.push()


def write_entry(result, temp_dir, repo):
    log_file_path = os.path.join(temp_dir, result['app'], (result['env'] + '.json'))
    with open(log_file_path, 'r', encoding='utf-8', newline='\n') as f:
        history = json.load(f)
    history.insert(0, result)
    with open(log_file_path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(history, f, indent=2, sort_keys=True, cls=Iso8601DateTimeEncoder)
    repo.index.add(log_file_path)
