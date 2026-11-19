import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { I18nService } from '../i18n/i18n.service';

@Component({
  selector: 'app-star-rating',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './star-rating.html',
  styleUrl: './star-rating.css',
})
export class StarRating {
  @Input() label = '';
  @Input() name = '';
  @Input() value: number | null = null;
  @Output() valueChange = new EventEmitter<number>();

  hoverValue: number | null = null;
  readonly stars = [1, 2, 3, 4, 5];
  constructor(public i18n: I18nService) {}

  get displayValue(): number | null {
    return this.hoverValue ?? this.value;
  }

  get valueLabel(): string {
    const keys = ['', 'ratingTerrible', 'ratingPoor', 'ratingOkay', 'ratingGood', 'ratingExcellent'];
    return this.value ? this.i18n.t(keys[this.value]) : this.i18n.t('ratingNotSelected');
  }

  setValue(value: number): void {
    this.value = value;
    this.valueChange.emit(value);
  }

  onKeydown(event: KeyboardEvent, index: number): void {
    let next = index;
    if (event.key === 'ArrowRight' || event.key === 'ArrowUp') next = Math.min(5, index + 1);
    else if (event.key === 'ArrowLeft' || event.key === 'ArrowDown') next = Math.max(1, index - 1);
    else if (event.key === 'Home') next = 1;
    else if (event.key === 'End') next = 5;
    else return;
    event.preventDefault();
    this.setValue(next);
    queueMicrotask(() => document.getElementById(`${this.name}-${next}`)?.focus());
  }
}
