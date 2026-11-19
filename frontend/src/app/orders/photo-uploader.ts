import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { I18nService } from '../i18n/i18n.service';

export interface ReviewPhotoFile {
  file: File;
  preview: string;
}

@Component({
  selector: 'app-photo-uploader',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './photo-uploader.html',
  styleUrl: './photo-uploader.css',
})
export class PhotoUploader {
  @Input() photos: ReviewPhotoFile[] = [];
  @Output() photosChange = new EventEmitter<ReviewPhotoFile[]>();

  dragActive = false;
  error = '';
  constructor(public i18n: I18nService) {}

  onFileInput(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.addFiles(input.files ? Array.from(input.files) : []);
    input.value = '';
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    this.dragActive = false;
    this.addFiles(event.dataTransfer?.files ? Array.from(event.dataTransfer.files) : []);
  }

  addFiles(files: File[]): void {
    this.error = '';
    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
    const next = [...this.photos];

    for (const file of files) {
      if (!allowedTypes.includes(file.type)) {
        this.error = this.i18n.t('reviewPhotoFormatError');
        continue;
      }
      if (file.size > 5 * 1024 * 1024) {
        this.error = this.i18n.t('reviewPhotoSizeError');
        continue;
      }
      if (next.length >= 3) {
        this.error = this.i18n.t('reviewPhotoLimitError');
        break;
      }
      next.push({ file, preview: URL.createObjectURL(file) });
    }

    this.photos = next;
    this.photosChange.emit(next);
  }

  removePhoto(index: number): void {
    const next = [...this.photos];
    URL.revokeObjectURL(next[index].preview);
    next.splice(index, 1);
    this.photos = next;
    this.error = '';
    this.photosChange.emit(next);
  }
}
