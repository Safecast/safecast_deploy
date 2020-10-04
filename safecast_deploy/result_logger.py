import datetime
import git
import json
import os
import sys
import tempfile


class Iso8601DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.datetime)):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


class ResultLogger():
    def __init__(self, stream=sys.stdout, log_git=True):
        self.log_git = log_git

    def log_result(self, result):
        self.write_stream(result)
        if self.log_git:
            self.log_git(result)

    def _log_git(self, result):
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

    def _write_stream(self, result):
        json.dump(result, self.stream, sort_keys=True, indent=2, cls=Iso8601DateTimeEncoder)
        print(file=self.stream)

    def _write_git_entry(self, result, temp_dir, repo):
        log_file_path = os.path.join(temp_dir, result['app'], (result['env'] + '.json'))

        if not os.path.exists(os.path.dirname(log_file_path)):
            os.mkdir(os.path.dirname(log_file_path))

        if os.path.exists(log_file_path):
            with open(log_file_path, 'r', encoding='utf-8', newline='\n') as f:
                history = json.load(f)
        else:
            history = []

        history.insert(0, result)
        with open(log_file_path, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(history, f, indent=2, sort_keys=True, cls=Iso8601DateTimeEncoder)
        repo.index.add(log_file_path)
