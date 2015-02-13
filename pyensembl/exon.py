from .locus import Locus

class Exon(Locus):
    def __init__(self, exon_id, db):

        if not isinstance(exon_id, str):
            raise TypeError(
                "Expected exon ID to be string, got %s : %s" % (
                    exon_id, type(exon_id)))

        self.id = exon_id
        self.db = db

        columns = [
            'seqname',
            'start',
            'end',
            'strand',
            'gene_name',
            'gene_id',
        ]

        result = self.db.query_one(
            select_column_names=columns,
            filter_column='exon_id',
            filter_value=exon_id,
            feature='exon',
            distinct=True)

        result_dict = {}
        for i, column_name in enumerate(columns):
            result_dict[column_name] = result[i]

        Locus.__init__(
            self,
            result_dict['seqname'],
            result_dict['start'],
            result_dict['end'],
            result_dict['strand'])

        self.gene_name = result_dict['gene_name']
        self.gene_id = result_dict['gene_id']


    def __str__(self):
        return "Exon(exon_id=%s, gene_name=%s, contig=%s, start=%d, end=%s)" % (
            self.id, self.gene_name, self.contig, self.start, self.end)

    def __repr__(self):
        return str(self)



    # possible annotations associated with exons
    _EXON_FEATURES = {'start_codon', 'stop_codon', 'UTR', 'CDS'}

    def _exon_feature_positions(self, feature):
        """
        Find start and end positions of features (such as start codons)
        which are contained within this exon.
        """
        if feature not in self._EXON_FEATURES:
            raise ValueError("Invalid exon feature: %s" % feature)

        # query for distinct ranges since, for example, multiple transcripts
        # often have the same start codon. Each transcript's start codon has
        # its own feature='start_codon' entry
        query = """
            SELECT DISTINCT start, end
            FROM ensembl
            WHERE feature = ?
            AND seqname = ?
            AND strand = ?
            AND start >= ?
            AND end <= ?
        """
        query_params = [
            feature,
            self.contig,
            self.strand,
            self.start,
            self.end,
        ]
        cursor = self.db.connection.execute(query, query_params)
        results = cursor.fetchall()

        # check to make sure we only got back integer values
        for (start, end) in results:
            assert isinstance(start, int), \
                "Invalid type %s for start position %s" % (
                    type(position), position)
            assert isinstance(end, int), \
                "Invalid type %s for end position %s" % (
                    type(position), position)
        return results


    @property
    def start_codon_positions(self):
        """
        Absolute positions of overlapping start codons.
        """
        return self._exon_feature_positions('start_codon')

    @property
    def stop_codon_positions(self):
        """
        Absolute positions of overlapping stop codons.
        """
        return self._exon_feature_positions('stop_codon')

    def _first_offset(self, start, end):
        relative_start, relative_end = self.offset_range(start, end)
        return min(relative_start, relative_end)

    def _exon_feature_offsets(self, feature):
        """
        Start and end offsets (relative to this exon) of features such as
        start_codon and stop_codon.
        """
        # start and end positions on the chromosome
        absolute_positions = self._exon_feature_positions(feature)
        results = []
        for start, end in absolute_positions:
            local_position = self._first_offset(start, end)
            results.append(local_position)
        return results

    @property
    def start_codon_offsets(self):
        """
        How many bases from the beginning of the exon (starting from 0)
        is the first base of the start codon?
        """
        return self._exon_feature_offsets('start_codon')


    @property
    def stop_codon_offsets(self):
        """
        How many bases from the beginning of the exon (starting from 0)
        is the first base of the stop codon?
        """
        return self._exon_feature_offsets('stop_codon')


    @property
    def contains_start_codon(self):
        """
        Does this exon contain a start codon in any transcript?
        """
        return len(self.start_codon_offsets) > 0

    @property
    def contains_stop_codon(self):
        """
        Does this exon contain a stop codon in any transcript?
        """
        return len(self.stop_codon_offsets) > 0


