import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { StarRating } from './star-rating';
import { PhotoUploader, ReviewPhotoFile } from './photo-uploader';
import { I18nService } from '../i18n/i18n.service';

export interface ReviewFormValue {
  restaurant_rating: number | null;
  food_rating: number | null;
  courier_rating: number | null;
  delivery_speed_rating: number | null;
  comment: string;
  photos: ReviewPhotoFile[];
}

@Component({
  selector: 'app-review-form',
  standalone: true,
  imports: [CommonModule, FormsModule, StarRating, PhotoUploader],
  templateUrl: './review-form.html',
  styleUrl: './review-form.css',
})
export class ReviewForm {
  @Input() value!: ReviewFormValue;
  @Input() submitting = false;
  @Input() error = '';
  @Input() success = '';
  @Output() submitted = new EventEmitter<ReviewFormValue>();

  attempted = false;
  constructor(public i18n: I18nService) {}

  get complete(): boolean {
    return !!this.value && [this.value.restaurant_rating, this.value.food_rating, this.value.courier_rating, this.value.delivery_speed_rating].every(x => Number.isInteger(x) && x! >= 1 && x! <= 5)
      && this.value.comment.trim().length >= 10 && this.value.comment.trim().length <= 1000;
  }

  submit(): void {
    this.attempted = true;
    if (!this.complete || this.submitting) return;
    this.submitted.emit({ ...this.value, photos: [...this.value.photos] });
  }

  setPhotos(photos: ReviewPhotoFile[]): void {
    this.value.photos = photos;
  }

  resizeTextarea(event: Event): void {
    const textarea = event.target as HTMLTextAreaElement;
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.max(112, textarea.scrollHeight)}px`;
  }
}
