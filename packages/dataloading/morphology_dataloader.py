import torch
from torch.nn.functional import log_softmax, pad 
from torch.nn.utils.rnn import pack_padded_sequence
from torch.utils.data import DataLoader
from torchtext.vocab import Vocab

from packages.dataloading.morphology_dataset import SigmorphonDataset

def collate_batch(
    batch,
    char_pipeline,
    tag_pipeline,
    char_vocab,
    tag_vocab,
    device,
    max_padding=25,
    pad_id=2,
):
    bs_id = torch.tensor([0], device=device)  # <s> token id
    eos_id = torch.tensor([1], device=device)  # </s> token id
    src_list, tag_list, tgt_list, src_lengths, tgt_lengths, is_hallucinated = [], [], [], [], [], []
    for (_src, _tgt, _tag, _is_hallucinated) in batch:
        processed_src = torch.cat(
            [
                bs_id,
                torch.tensor(
                    char_vocab(char_pipeline(_src)) ,
                    dtype=torch.int64,
                    device=device,
                ),
                eos_id,
            ],
            0,
        )
        processed_tag = torch.cat(
            [
                bs_id,
                torch.tensor(
                    tag_vocab(tag_pipeline(_tag)),
                    dtype=torch.int64,
                    device=device
                ),
                eos_id
            ],
            0
        )
        processed_tgt = torch.cat(
            [
                bs_id,
                torch.tensor(
                    char_vocab(char_pipeline(_tgt)),
                    dtype=torch.int64,
                    device=device,
                ),
                eos_id,
            ],
            0,
        )
        # TODO: understand how this padding code works.
        src_list.append(
            # warning - overwrites values for negative values of padding - len
            pad(
                processed_src,
                (
                    0,
                    max_padding - len(processed_src),
                ),
                value=pad_id,
            )
        )
        tgt_list.append(
            pad(
                processed_tgt,
                (0, max_padding - len(processed_tgt)),
                value=pad_id,
            )
        )

        tag_list.append(
            processed_tag
            # pad(
            #     processed_tag,
            #     (0, max_padding - len(processed_tag)),
            # )
        )

        is_hallucinated.append(
            _is_hallucinated
        )

        src_lengths.append(len(_src) + 2) # +2 for bos and eos
        tgt_lengths.append(len(_tgt) + 2)

    # src = torch.stack(pack_padded_sequence(torch.tensor(src_list), src_lengths))
    # tgt = torch.stack(pack_padded_sequence(torch.tensor(tgt_list), tgt_lengths))
    src = torch.stack((src_list) )
    tgt = torch.stack((tgt_list))
    tag = torch.stack((tag_list))
    src_lengths = torch.tensor(src_lengths, device=device)
    tgt_lengths = torch.tensor(tgt_lengths, device=device)
    is_hallucinated = torch.tensor(is_hallucinated, dtype=torch.bool, device=device)
    return (src, tgt, tag, src_lengths, tgt_lengths, is_hallucinated)

def create_dataloader(dataset: SigmorphonDataset, batch_size: int, char_vocab: Vocab , tag_vocab: Vocab, device: str, shuffle=True, drop_last=True):
    def collate_fn(batch):
        return collate_batch(
            batch,
            list,
            lambda tag: tag.split(';'),
            char_vocab,
            tag_vocab,
            device,
            pad_id=char_vocab.get_stoi()["<blank>"]
        )
    dataloader = DataLoader(
        dataset,
        shuffle = shuffle,
        batch_size=batch_size,
        drop_last=drop_last,
        collate_fn=collate_fn
    )
    return dataloader