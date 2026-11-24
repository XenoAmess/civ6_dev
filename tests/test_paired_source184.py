"""Exercise the real source184 consumers; transport remains synthetic."""
import test_paired_source183 as previous


class Source184PairedTests(previous.Source183PairedTests):
    source_version = 184
